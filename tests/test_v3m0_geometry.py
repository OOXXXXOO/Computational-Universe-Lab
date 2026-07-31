from __future__ import annotations

import dataclasses
import inspect
import unittest

import rulespace_v3.geometry as geometry
from rulespace_v3.blocks import ResponseBlock
from rulespace_v3.calibration_authority import CalibrationApplicationPermit
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze


class GeometryThresholdAuthorityContractTests(unittest.TestCase):
    def test_exact_wire_surfaces_are_frozen(self) -> None:
        self.assertEqual(
            tuple(geometry.GeometryCoverageThresholdInstanceAudit.__dataclass_fields__),
            (
                "audit_schema_version",
                "application_spec",
                "permit",
                "response_block",
                "g_spectrum",
                "c_spectrum",
                "measured_geometry_side_labels",
                "measured_coverage_side_labels",
                "expected_geometry_side_labels",
                "expected_coverage_side_labels",
                "geometry_signed_threshold_margins",
                "coverage_signed_threshold_margins",
                "geometry_minimum_absolute_margin",
                "coverage_minimum_absolute_margin",
                "audit_sha",
            ),
        )
        self.assertEqual(
            tuple(
                geometry.GeometryCoverageThresholdControlEvidence.__dataclass_fields__
            ),
            (
                "evidence_schema_version",
                "parent_freeze",
                "instance_audits",
                "evidence_sha",
            ),
        )
        self.assertEqual(
            tuple(geometry.GeometryCoverageThresholdCalibration.__dataclass_fields__),
            (
                "calibration_schema_version",
                "tau_geom",
                "geom_ambiguity_half_width",
                "tau_cover",
                "cover_ambiguity_half_width",
                "control_evidence",
                "calibration_sha",
            ),
        )

    def test_public_authority_signatures_accept_no_caller_geometry(self) -> None:
        self.assertEqual(
            tuple(
                inspect.signature(
                    geometry.build_geometry_coverage_threshold_calibration
                ).parameters
            ),
            ("blocks", "permits"),
        )
        self.assertEqual(
            tuple(
                inspect.signature(
                    geometry.verify_geometry_coverage_threshold_calibration
                ).parameters
            ),
            ("raw", "blocks", "permits"),
        )
        self.assertEqual(
            tuple(inspect.signature(geometry.compute_geometry).parameters),
            ("block", "calibration"),
        )
        self.assertFalse(hasattr(geometry, "compute_geometry_spectrum"))
        self.assertFalse(hasattr(geometry, "audit_degenerate_rotations"))

    def test_wrapper_is_module_issued_and_raw_records_are_inert(self) -> None:
        with self.assertRaises(TypeError):
            geometry.VerifiedGeometryCoverageThresholdCalibration(
                object(),
                object(),
                "0" * 64,
            )
        forged = object.__new__(geometry.VerifiedGeometryCoverageThresholdCalibration)
        with self.assertRaises((TypeError, ValueError)):
            geometry.compute_geometry(object(), forged)

    def test_builders_require_exact_live_capability_tuples(self) -> None:
        with self.assertRaisesRegex(TypeError, "blocks must be an exact tuple"):
            geometry.build_geometry_coverage_threshold_calibration([], ())
        with self.assertRaisesRegex(TypeError, "permits must be an exact tuple"):
            geometry.build_geometry_coverage_threshold_calibration((), [])
        with self.assertRaisesRegex(ValueError, "C15-C17"):
            geometry.build_geometry_coverage_threshold_calibration((), ())
        with self.assertRaisesRegex(TypeError, "VerifiedResponseBlock"):
            geometry.build_geometry_coverage_threshold_calibration(
                (object(),),
                (object(),),
            )

    def test_hydrator_rejects_non_raw_and_unknown_wire_fields_first(self) -> None:
        with self.assertRaisesRegex(
            TypeError,
            "GeometryCoverageThresholdCalibration",
        ):
            geometry.verify_geometry_coverage_threshold_calibration(
                object(),
                (),
                (),
            )

        raw = object.__new__(geometry.GeometryCoverageThresholdCalibration)
        for field, value in (
            (
                "calibration_schema_version",
                geometry.GEOMETRY_COVERAGE_THRESHOLD_CALIBRATION_SCHEMA_VERSION,
            ),
            ("tau_geom", 0.05),
            ("geom_ambiguity_half_width", 0.01),
            ("tau_cover", 0.5),
            ("cover_ambiguity_half_width", 0.1),
            ("control_evidence", object()),
            ("calibration_sha", "0" * 64),
            ("caller_threshold", 0.9),
        ):
            object.__setattr__(raw, field, value)
        with self.assertRaisesRegex(ValueError, "missing or unknown fields"):
            geometry.geometry_coverage_threshold_calibration_payload(raw)

    def test_missing_task12_geometry_operators_are_explicitly_frozen(self) -> None:
        self.assertEqual(
            geometry.GEOMETRY_AUTHORITY_REQUIRED_TASK12_FIELDS,
            (
                "kernel_basis",
                "physical_quotient_map",
                "physical_quotient_metric",
                "target_physical_representatives",
            ),
        )
        self.assertTrue(
            issubclass(
                geometry.GeometryAuthorityUnavailableError,
                RuntimeError,
            )
        )

    def test_expected_threshold_sides_are_derived_from_parent_predictions(self) -> None:
        parent = issue_v3m0_parent_freeze().manifest
        observed = {}
        for application in parent.synthetic_control_application_specs:
            if application.control_case_id in (
                geometry.GEOMETRY_THRESHOLD_CONTROL_CASE_IDS
            ):
                observed[application.control_case_id] = (
                    geometry._expected_threshold_labels(application)
                )
        self.assertEqual(
            observed,
            {
                "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY": (
                    (
                        "above",
                        "above",
                        "below",
                        "above",
                        "above",
                        "above",
                        "above",
                        "above",
                    ),
                    (),
                ),
                "C16_COVERAGE_025_075": ((), ("below", "above")),
                "C17_QUOTIENT_GAUGE_COVERAGE": (
                    (),
                    ("below", "above"),
                ),
            },
        )

    def test_instance_audit_recomputes_strict_sides_and_margins(self) -> None:
        parent = issue_v3m0_parent_freeze().manifest
        application = next(
            item
            for item in parent.synthetic_control_application_specs
            if item.control_case_id == "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY"
        )
        g_spectrum = (0.039, 0.05, 0.061)
        c_spectrum = (0.39, 0.5, 0.61)
        audit = geometry.GeometryCoverageThresholdInstanceAudit(
            audit_schema_version=(
                geometry.GEOMETRY_COVERAGE_THRESHOLD_INSTANCE_AUDIT_SCHEMA_VERSION
            ),
            application_spec=application,
            permit=object.__new__(CalibrationApplicationPermit),
            response_block=object.__new__(ResponseBlock),
            g_spectrum=g_spectrum,
            c_spectrum=c_spectrum,
            measured_geometry_side_labels=("below", "grey", "above"),
            measured_coverage_side_labels=("below", "grey", "above"),
            expected_geometry_side_labels=(),
            expected_coverage_side_labels=(),
            geometry_signed_threshold_margins=tuple(
                value - geometry.GEOMETRY_THRESHOLD for value in g_spectrum
            ),
            coverage_signed_threshold_margins=tuple(
                value - geometry.COVERAGE_THRESHOLD for value in c_spectrum
            ),
            geometry_minimum_absolute_margin=0.0,
            coverage_minimum_absolute_margin=0.0,
            audit_sha="0" * 64,
        )
        with self.assertRaisesRegex(ValueError, "were not recomputed"):
            dataclasses.replace(
                audit,
                measured_geometry_side_labels=("below", "below", "above"),
            )
        with self.assertRaisesRegex(ValueError, "signed margins"):
            dataclasses.replace(
                audit,
                geometry_signed_threshold_margins=(0.0, 0.0, 0.0),
            )

    def test_calibration_threshold_wires_require_exact_floats(self) -> None:
        class FloatSubclass(float):
            pass

        with self.assertRaisesRegex(ValueError, "tau_geom"):
            geometry.GeometryCoverageThresholdCalibration(
                calibration_schema_version=(
                    geometry.GEOMETRY_COVERAGE_THRESHOLD_CALIBRATION_SCHEMA_VERSION
                ),
                tau_geom=FloatSubclass(0.05),
                geom_ambiguity_half_width=0.01,
                tau_cover=0.5,
                cover_ambiguity_half_width=0.1,
                control_evidence=object.__new__(
                    geometry.GeometryCoverageThresholdControlEvidence
                ),
                calibration_sha="0" * 64,
            )


if __name__ == "__main__":
    unittest.main()
