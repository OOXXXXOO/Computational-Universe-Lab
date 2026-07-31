from __future__ import annotations

import copy
import dataclasses
import dis
import gc
import hashlib
import inspect
import math
import struct
import unittest
import weakref
from pathlib import Path
from unittest import mock

import numpy as np

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import (
    basis_manifest_array,
    build_basis_manifest,
    frozen_tensor_array,
)
from rulespace_v3.parent_freeze import (
    APPLICATION_CONTROL_CASE_IDS,
    IMPLEMENTATION_PLAN_SOURCE_PATH,
    PARENT_FREEZE_SCHEMA_VERSION,
    PROGRAM_ID,
    TASK9_COMMIT_SHA,
    TASKBOOK_SOURCE_PATH,
    ParentFreezeManifest,
    SyntheticApplicationBasisProtocol,
    SyntheticApplicationGridProtocol,
    SyntheticApplicationOperation,
    SyntheticApplicationPredictionProfile,
    SyntheticApplicationProtocolConstants,
    SyntheticApplicationReadoutProtocol,
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
        operation_sha=canonical_sha(synthetic_application_operation_payload(operation)),
    )


def _resign_basis_protocol(
    protocol: SyntheticApplicationBasisProtocol,
) -> SyntheticApplicationBasisProtocol:
    return dataclasses.replace(
        protocol,
        protocol_sha=canonical_sha(
            synthetic_application_basis_protocol_payload(protocol)
        ),
    )


def _resign_grid_protocol(
    protocol: SyntheticApplicationGridProtocol,
) -> SyntheticApplicationGridProtocol:
    return dataclasses.replace(
        protocol,
        protocol_sha=canonical_sha(
            synthetic_application_grid_protocol_payload(protocol)
        ),
    )


def _resign_readout_protocol(
    protocol: SyntheticApplicationReadoutProtocol,
) -> SyntheticApplicationReadoutProtocol:
    return dataclasses.replace(
        protocol,
        protocol_sha=canonical_sha(
            synthetic_application_readout_protocol_payload(protocol)
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

    def test_c01_c03_mechanically_match_the_task8_quarter_turn_controls(
        self,
    ) -> None:
        specs = {
            spec.control_case_id: spec
            for spec in self.manifest.synthetic_control_application_specs[:3]
        }
        expected = {
            "C01_BLIND_HOLDOUT_FULL": (
                ("x.000", "y.000"),
                np.asarray(((1.0, 0.0),), dtype=np.complex128),
                np.asarray(((0.0, 1.0),), dtype=np.complex128),
                1,
            ),
            "C02_CONDITIONED_ZERO": (
                ("x.000", "y.000"),
                np.asarray(((1.0, 0.0),), dtype=np.complex128),
                np.asarray(((0.0, 1.0),), dtype=np.complex128),
                1,
            ),
            "C03_EQUAL_RANK_DIRECT_SUM": (
                ("x.b.000", "y.b.000", "x.c.001", "y.c.001"),
                np.asarray(
                    (
                        (1.0, 0.0, 0.0, 0.0),
                        (0.0, 0.0, 1.0, 0.0),
                    ),
                    dtype=np.complex128,
                ),
                np.asarray(
                    (
                        (0.0, 1.0, 0.0, 0.0),
                        (0.0, 0.0, 0.0, 1.0),
                    ),
                    dtype=np.complex128,
                ),
                2,
            ),
        }
        positive_quarter_turn_band = (
            math.pi / 2.0 - 0.25,
            math.pi / 2.0 + 0.25,
        )

        for control_case_id, (
            channels,
            source_vectors,
            readout_vectors,
            actual_rank,
        ) in expected.items():
            with self.subTest(control_case_id=control_case_id):
                spec = specs[control_case_id]
                basis = spec.basis_protocol
                self.assertEqual(
                    basis.source_basis.state_schema_id,
                    "state.synthetic.local-linear.v1",
                )
                self.assertEqual(
                    basis.readout_basis.state_schema_id,
                    "state.synthetic.local-linear.v1",
                )
                self.assertEqual(basis.source_basis.channel_order, channels)
                self.assertEqual(basis.readout_basis.channel_order, channels)
                np.testing.assert_array_equal(
                    basis_manifest_array(basis.source_basis),
                    source_vectors,
                )
                np.testing.assert_array_equal(
                    basis_manifest_array(basis.readout_basis),
                    readout_vectors,
                )
                self.assertEqual(
                    spec.grid_protocol.preregistered_phase_bands,
                    (positive_quarter_turn_band,),
                )
                self.assertEqual(
                    spec.grid_protocol.expected_shell_rank,
                    actual_rank,
                )

                dimension = source_vectors.shape[0]
                identity = np.eye(dimension, dtype=np.complex128)
                readout = spec.readout_protocol
                for tensor in (
                    readout.source_metric_whitener,
                    readout.h_metric_whitener,
                    readout.curvature_incidence_operator,
                    readout.curvature_metric_whitener,
                ):
                    np.testing.assert_array_equal(
                        frozen_tensor_array(tensor),
                        identity,
                    )

        self.assertEqual(
            tuple(
                len(
                    _exact_values(
                        specs[control_case_id].expected_prediction_profile
                    )["survival-spectrum"]
                )
                for control_case_id in (
                    "C01_BLIND_HOLDOUT_FULL",
                    "C02_CONDITIONED_ZERO",
                    "C03_EQUAL_RANK_DIRECT_SUM",
                )
            ),
            (1, 1, 2),
        )
        integer_parameters = {
            control_case_id: {
                name: wire.integer_value
                for operation in spec.operations
                for name, wire in operation.parameters
                if wire.value_kind == "integer"
            }
            for control_case_id, spec in specs.items()
        }
        self.assertEqual(
            integer_parameters["C01_BLIND_HOLDOUT_FULL"]["response-rank"],
            1,
        )
        self.assertEqual(
            integer_parameters["C01_BLIND_HOLDOUT_FULL"]["target-rank"],
            1,
        )
        self.assertEqual(
            integer_parameters["C02_CONDITIONED_ZERO"]["response-rank"],
            1,
        )
        self.assertEqual(
            integer_parameters["C03_EQUAL_RANK_DIRECT_SUM"]["response-rank"],
            2,
        )
        self.assertEqual(
            (
                integer_parameters["C03_EQUAL_RANK_DIRECT_SUM"]["left-rank"],
                integer_parameters["C03_EQUAL_RANK_DIRECT_SUM"]["right-rank"],
            ),
            (1, 1),
        )

    def test_c04_c20_application_contract_hashes_remain_unchanged(self) -> None:
        expected_application_shas = (
            "5ded5e86d7111d8341acfff1c7efc1de5113a466ab40dc2f8176f7ac049fa43b",
            "99a23718bdfe401c2e202a5fe270092b315c765390e06371872635811c02b530",
            "ce62fe83dd692594d7c90e1f136ad9d57844d553b6f0c123237da001802ba94c",
            "52f45380222bcaba4a3b6b727fa48234bcdb985258511bda4ec96c6db6d6a4bc",
            "9e64f4cdce70efa204307a02ef2d1e3ae888a78ff21fa5cf226abd9f3aefdbf8",
            "7249cebef57a87fd2683349dfef8564546fa6a605b41cd930052f2295c654e9c",
            "6bbd1a319a8f7c7c6faae86e5ea8d133bb9d01048fe240e8181ceb1ba0e3081c",
            "afbeb4574047d87e782d1e16df401ec6756c743f7ad63261f553c1c04c75415a",
            "0e26db92cc91e6f26f4b866935cdc7125776ad262d0a641ef92a2d76ad0adf02",
            "cfed9e8435c82f7ede2de9468f8914299fa3b3814d0010005cf1fabf11c89d49",
            "6b3b4dbbef5ff53def47b3e57310b956de5ce94d78d5f600b2fdcf866fb05b33",
            "556b7483b2f9c1dd5acdcdfa907430d4a252687326500a53d83573bc12c11d13",
            "6f13006080dc9e0508431c031c866bb3b4a61d6e51f3766881ba974435e1b6e3",
            "e0c5a3cbdf68313824dbffd24f5f53e1e66c90e8d0eb832632c1e9c131e2eac6",
            "0800fe5100405063a4668ba2a684e2d5a676b518ce3d1889fa88d406a860a646",
            "094db4d13d66782859002c84bd6aef1789e0a2a5f91a04b4d2d5ae1939d68cda",
            "865cd29861af476b84e9c5f4a19b8eb87d9b89ec129ab2e50cc59f77b098afe8",
        )
        untouched = self.manifest.synthetic_control_application_specs[3:]
        self.assertEqual(
            tuple(spec.application_spec_sha for spec in untouched),
            expected_application_shas,
        )
        self.assertEqual(
            {
                (
                    spec.basis_protocol.protocol_sha,
                    spec.grid_protocol.protocol_sha,
                    spec.readout_protocol.protocol_sha,
                )
                for spec in untouched
            },
            {
                (
                    "ec3d0d0e641646f5200527c26616482b61ba97501e99dbff7421a956c1e5df74",
                    "88d9a871e0b043e925ab71fb0982566d74f7a5043f0a149a102129759f279a00",
                    "4c93f9ff88e652a01f140e52be0b2a19cd4c5587efbe4b3d8a6cabe1e297ac05",
                )
            },
        )

    def test_c20_freezes_four_point_full_window_before_h3_deletion(self) -> None:
        spec = next(
            item
            for item in self.manifest.synthetic_control_application_specs
            if item.control_case_id == "C20_DM26_CLEAN_ZERO_TRUE_FLOOR"
        )
        series_operations = tuple(
            operation
            for operation in spec.operations
            if operation.operation_kind == "deterministic-series-v1"
        )
        self.assertEqual(len(series_operations), 2)
        for operation in series_operations:
            self.assertEqual(
                tuple(
                    name
                    for name, _ in operation.parameters
                    if name.startswith("sample-")
                ),
                ("sample-0", "sample-1", "sample-2", "sample-3"),
            )
        exact = dict(spec.expected_prediction_profile.expected_exact_values)
        self.assertEqual(len(exact["clean-zero-series"]), 4)
        self.assertEqual(len(exact["true-floor-series"]), 4)

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
            self.assertGreater(
                len(spec.readout_protocol.source_metric_whitener.values_wire), 0
            )
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
            canonical_sha(synthetic_application_protocol_constants_payload(constants)),
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
                    synthetic_application_basis_protocol_payload(spec.basis_protocol)
                ),
            )
            self.assertEqual(
                spec.grid_protocol.protocol_sha,
                canonical_sha(
                    synthetic_application_grid_protocol_payload(spec.grid_protocol)
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
                    canonical_sha(synthetic_application_operation_payload(operation)),
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
                inspect.signature(verify_synthetic_control_application_spec).parameters
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
                    + len(spec.expected_prediction_profile.expected_qualitative_labels),
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
                for wire in _exact_values(c04.expected_prediction_profile)[
                    "survival-spectrum"
                ]
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
                for wire in _exact_values(c11.expected_prediction_profile)[
                    "input-amplitude"
                ]
            ),
            (_float_bits(0.0), _float_bits(0.5), _float_bits(1.0)),
        )
        outcomes = _exact_values(c11.expected_prediction_profile)["causal-coordinate"]
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

    def test_single_spec_verifier_rejects_every_resigned_noncanonical_field(
        self,
    ) -> None:
        spec = self.manifest.synthetic_control_application_specs[3]

        renamed_instance_id = f"{spec.application_instance_id}.post-hoc"

        def renamed_id(value: str) -> str:
            self.assertTrue(value.startswith(spec.application_instance_id))
            return renamed_instance_id + value[len(spec.application_instance_id) :]

        renamed_operations = tuple(
            _resign_operation(
                dataclasses.replace(
                    operation,
                    operation_instance_id=renamed_id(operation.operation_instance_id),
                    input_operation_instance_ids=tuple(
                        renamed_id(dependency)
                        for dependency in operation.input_operation_instance_ids
                    ),
                )
            )
            for operation in spec.operations
        )
        renamed_application = _resign_spec(
            dataclasses.replace(
                spec,
                application_instance_id=renamed_instance_id,
                operations=renamed_operations,
                output_operation_instance_ids=tuple(
                    renamed_id(output) for output in spec.output_operation_instance_ids
                ),
            )
        )

        basis = spec.basis_protocol
        rotated = np.array(
            ((0.0, 1.0), (-1.0, 0.0)),
            dtype=np.complex128,
        )
        changed_basis = _resign_basis_protocol(
            dataclasses.replace(
                basis,
                source_basis=build_basis_manifest(
                    role="source",
                    state_schema_id=basis.source_basis.state_schema_id,
                    channel_order=basis.source_basis.channel_order,
                    vectors=rotated,
                ),
                readout_basis=build_basis_manifest(
                    role="readout",
                    state_schema_id=basis.readout_basis.state_schema_id,
                    channel_order=basis.readout_basis.channel_order,
                    vectors=rotated,
                ),
            )
        )
        changed_grid = _resign_grid_protocol(
            dataclasses.replace(
                spec.grid_protocol,
                preregistered_phase_bands=((-0.125, 0.125),),
            )
        )
        changed_readout = _resign_readout_protocol(
            dataclasses.replace(
                spec.readout_protocol,
                curvature_normalizer_id="post-hoc-normalizer",
            )
        )
        changed_constants = _resign_constants(
            dataclasses.replace(
                spec.protocol_constant_payload,
                max_operation_count=(
                    spec.protocol_constant_payload.max_operation_count + 1
                ),
            )
        )

        first_operation = spec.operations[0]
        changed_operation = _resign_operation(
            dataclasses.replace(
                first_operation,
                parameters=(
                    (
                        "response-rank",
                        TaggedScalarWire("integer", 3, None, None, None),
                    ),
                ),
            )
        )
        changed_operations = (
            changed_operation,
            *spec.operations[1:],
        )
        changed_outputs = tuple(
            sorted(
                (
                    *spec.output_operation_instance_ids,
                    first_operation.operation_instance_id,
                )
            )
        )
        changed_profile = _resign_prediction_profile(
            dataclasses.replace(
                spec.expected_prediction_profile,
                prediction_profile_id="v3m0.synthetic-prediction.post-hoc",
            )
        )

        mutations = {
            "application-schema": _resign_spec(
                dataclasses.replace(
                    spec,
                    application_schema_version="post-hoc-schema",
                )
            ),
            "control-case": _resign_spec(
                dataclasses.replace(
                    spec,
                    control_case_id=APPLICATION_CONTROL_CASE_IDS[4],
                )
            ),
            "application-instance": renamed_application,
            "builder": _resign_spec(
                dataclasses.replace(spec, builder_id="post-hoc-builder")
            ),
            "basis-protocol": _resign_spec(
                dataclasses.replace(spec, basis_protocol=changed_basis)
            ),
            "grid-protocol": _resign_spec(
                dataclasses.replace(spec, grid_protocol=changed_grid)
            ),
            "readout-protocol": _resign_spec(
                dataclasses.replace(spec, readout_protocol=changed_readout)
            ),
            "protocol-constants": _resign_spec(
                dataclasses.replace(
                    spec,
                    protocol_constant_payload=changed_constants,
                )
            ),
            "operations": _resign_spec(
                dataclasses.replace(spec, operations=changed_operations)
            ),
            "outputs": _resign_spec(
                dataclasses.replace(
                    spec,
                    output_operation_instance_ids=changed_outputs,
                )
            ),
            "required-stages": _resign_spec(
                dataclasses.replace(
                    spec,
                    required_pipeline_stages=(
                        *spec.required_pipeline_stages,
                        "post-hoc-stage",
                    ),
                )
            ),
            "prediction-profile": _resign_spec(
                dataclasses.replace(
                    spec,
                    expected_prediction_profile_id=(
                        changed_profile.prediction_profile_id
                    ),
                    expected_prediction_profile=changed_profile,
                )
            ),
            "evidence-schema": _resign_spec(
                dataclasses.replace(
                    spec,
                    expected_control_evidence_schema=("post-hoc-control-evidence"),
                )
            ),
        }

        for field, changed_spec in mutations.items():
            with self.subTest(field=field):
                self.assertEqual(
                    changed_spec.application_spec_sha,
                    canonical_sha(
                        synthetic_control_application_spec_payload(changed_spec)
                    ),
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "canonical|closed|match|unexpected",
                ):
                    verify_synthetic_control_application_spec(changed_spec)

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
        dangling_spec = _resign_spec(dataclasses.replace(spec, operations=(dangling,)))
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

        duplicate = _resign_spec(dataclasses.replace(spec, operations=(first, first)))
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
        with self.assertRaisesRegex(
            ValueError,
            "canonical|closed|freeze|match",
        ):
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
    def test_parent_closed_body_and_codec_rebinding_cannot_forge_issuance(
        self,
    ) -> None:
        import rulespace_v3.parent_freeze as parent_freeze

        baseline = issue_v3m0_parent_freeze().manifest
        provisional = dataclasses.replace(
            baseline,
            program_id="forged-program",
            parent_freeze_sha="0" * 64,
        )
        forged = dataclasses.replace(
            provisional,
            parent_freeze_sha=canonical_sha(
                parent_freeze_manifest_payload(provisional)
            ),
        )
        with (
            mock.patch.object(
                parent_freeze,
                "PROGRAM_ID",
                "forged-program",
            ),
            mock.patch.object(
                parent_freeze,
                "_CLOSED_PARENT_FREEZE",
                forged,
            ),
            mock.patch.object(
                parent_freeze,
                "canonical_sha",
                return_value="0" * 64,
            ),
            mock.patch.object(
                parent_freeze,
                "_manifest_record",
                return_value={},
            ),
        ):
            observed = issue_v3m0_parent_freeze().manifest
        self.assertEqual(observed, baseline)

    def test_raw_hydrator_rejects_recursive_unknowns_and_subclasses(
        self,
    ) -> None:
        issued = issue_v3m0_parent_freeze()
        targets = (
            lambda raw: raw,
            lambda raw: raw.synthetic_control_application_specs[0],
            lambda raw: raw.synthetic_control_application_specs[0].basis_protocol,
            lambda raw: raw.synthetic_control_application_specs[0].grid_protocol,
            lambda raw: raw.synthetic_control_application_specs[0].readout_protocol,
            lambda raw: raw.protocol_constant_payload,
            lambda raw: (
                raw.synthetic_control_application_specs[0].expected_prediction_profile
            ),
            lambda raw: raw.synthetic_control_application_specs[0].operations[0],
        )
        for select in targets:
            raw = copy.deepcopy(issued.manifest)
            object.__setattr__(
                select(raw),
                "caller_unknown",
                "forbidden",
            )
            with self.subTest(target=type(select(raw)).__name__):
                with self.assertRaisesRegex(
                    (TypeError, ValueError),
                    "exact|unknown|record type",
                ):
                    verify_parent_freeze(raw)

        class HostileManifest(ParentFreezeManifest):
            pass

        raw = issued.manifest
        hostile = HostileManifest(
            raw.parent_freeze_schema_version,
            raw.program_id,
            raw.parent_v2_sha,
            raw.task9_commit_sha,
            raw.taskbook_source_sha,
            raw.implementation_plan_source_sha,
            raw.synthetic_control_application_specs,
            raw.protocol_constant_payload,
            raw.source_closure,
            raw.parent_freeze_sha,
        )
        with self.assertRaisesRegex(
            (TypeError, ValueError),
            "exact|record type|ParentFreezeManifest",
        ):
            verify_parent_freeze(hostile)

    def test_reverifier_has_no_module_global_loads(self) -> None:
        offenders = [
            (instruction.opname, instruction.argval)
            for instruction in dis.get_instructions(_reverify_verified_parent_freeze)
            if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"}
        ]
        self.assertEqual(offenders, [])

    def test_deepcopy_global_rebinding_cannot_forge_returned_manifest(
        self,
    ) -> None:
        import rulespace_v3.parent_freeze as parent_freeze

        issued = issue_v3m0_parent_freeze()
        expected = issued.manifest
        live_registry = next(
            cell.cell_contents
            for cell in (
                parent_freeze._reverify_verified_parent_freeze.__closure__ or ()
            )
            if type(cell.cell_contents) is dict and id(issued) in cell.cell_contents
        )
        authority = live_registry[id(issued)][1]
        forged = dataclasses.replace(
            authority.manifest,
            parent_freeze_sha="0" * 64,
        )
        original_deepcopy = parent_freeze.copy.deepcopy

        def hostile_deepcopy(value):
            if value is authority.manifest:
                return forged
            return original_deepcopy(value)

        with mock.patch.object(
            parent_freeze.copy,
            "deepcopy",
            side_effect=hostile_deepcopy,
        ):
            observed = _reverify_verified_parent_freeze(issued)
        self.assertEqual(observed, expected)

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
