"""Authority-neutral schema tests for the pre-response geometry protocol v3."""

from __future__ import annotations

from dataclasses import fields, replace
import importlib
import math
from typing import Optional
import unittest

import numpy as np

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor, frozen_tensor_array


def _sha(index: int) -> str:
    return f"{index:064x}"


def _protocol():
    try:
        return importlib.import_module("rulespace_v3.geometry_protocol_v3")
    except ModuleNotFoundError as exc:
        raise AssertionError("geometry protocol v3 module is missing") from exc


class GeometryProtocolV3Tests(unittest.TestCase):
    def _context(
        self,
        kind: str,
        *,
        scenario_id: Optional[str] = None,
        selected_fejer_order: int = 256,
    ):
        protocol = _protocol()
        scenario_by_kind = {
            protocol.C15_QUOTIENT_SPECTRUM: (
                "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY",
                "v3m0.synthetic-control.c15.v1.scenario.full-h.v1",
                ("TT0", "TT1", "Gauge", "Row"),
                None,
                None,
                False,
                4,
            ),
            protocol.C16_COVERAGE_CONTROL: (
                "C16_COVERAGE_025_075",
                "v3m0.synthetic-control.c16.v1.scenario.coverage-low.v1",
                ("coverage-probe",),
                0.25,
                None,
                False,
                5,
            ),
            protocol.C17_QUOTIENT_GAUGE_GRAPH: (
                "C17_QUOTIENT_GAUGE_COVERAGE",
                "v3m0.synthetic-control.c17.v1.scenario.quotient-gauge.v1",
                ("dressed-coverage-probe-0", "dressed-coverage-probe-1"),
                None,
                8.0,
                False,
                1,
            ),
            protocol.C18_INDEPENDENT_UNARY: (
                "C18_ABLATED_INDEPENDENT_UNARY",
                "v3m0.synthetic-control.c18.v1.scenario.independent-unary.v1",
                ("actual-source-q0", "matched-new-source-q1"),
                None,
                None,
                False,
                1,
            ),
            protocol.C19_OBSERVER_COLLAPSE_CONDITIONS: (
                "C19_FULL_POSITIVE_OBSERVER_COLLAPSE",
                "v3m0.synthetic-control.c19.v1.scenario.observer-collapse.v1",
                ("full-positive-0", "full-positive-1"),
                None,
                None,
                True,
                1,
            ),
        }
        (
            control_case_id,
            default_scenario_id,
            sectors,
            coverage,
            gauge,
            observer,
            source_count,
        ) = scenario_by_kind[kind]
        scenario_id = default_scenario_id if scenario_id is None else scenario_id
        if kind == protocol.C15_QUOTIENT_SPECTRUM:
            sectors = {
                "v3m0.synthetic-control.c15.v1.scenario.full-h.v1": (
                    "TT0",
                    "TT1",
                    "Gauge",
                    "Row",
                ),
                "v3m0.synthetic-control.c15.v1.scenario.low-rank-tt.v1": ("TT0",),
                "v3m0.synthetic-control.c15.v1.scenario.tt.v1": (
                    "TT0",
                    "TT1",
                ),
                "v3m0.synthetic-control.c15.v1.scenario.tt-plus-row.v1": (
                    "TT0",
                    "TT1",
                    "Row",
                ),
            }[scenario_id]
        if (
            kind == protocol.C16_COVERAGE_CONTROL
            and scenario_id == "v3m0.synthetic-control.c16.v1.scenario.coverage-high.v1"
        ):
            coverage = 0.75
        recipe_sha = _sha(100 + tuple(protocol.GEOMETRY_KINDS_V3).index(kind))
        source_shas = [_sha(200 + index) for index in range(source_count)]
        if kind == protocol.C15_QUOTIENT_SPECTRUM:
            c15_index = {
                "v3m0.synthetic-control.c15.v1.scenario.full-h.v1": 0,
                "v3m0.synthetic-control.c15.v1.scenario.low-rank-tt.v1": 1,
                "v3m0.synthetic-control.c15.v1.scenario.tt.v1": 2,
                "v3m0.synthetic-control.c15.v1.scenario.tt-plus-row.v1": 3,
            }[scenario_id]
            source_shas[c15_index] = recipe_sha
        else:
            source_shas[-1] = recipe_sha
        provisional = protocol.GeometryAnalyticContextV2(
            context_schema_version=(
                protocol.GEOMETRY_ANALYTIC_CONTEXT_V2_SCHEMA_VERSION
            ),
            geometry_kind=kind,
            control_case_id=control_case_id,
            scenario_id=scenario_id,
            scenario_sha=_sha(1),
            recipe_sha=recipe_sha,
            operation_dag_sha=_sha(2),
            compiled_contract_sha=_sha(3),
            geometry_derivation_source_id=(
                protocol.GEOMETRY_DERIVATION_SOURCE_ID_BY_KIND[kind]
            ),
            semantic_sector_names=sectors,
            selected_fejer_order=selected_fejer_order,
            analytic_source_recipe_shas=tuple(source_shas),
            coverage_control=coverage,
            gauge_amplitude=gauge,
            observer_collapse_expected=observer,
            context_sha="0" * 64,
        )
        context = replace(
            provisional,
            context_sha=canonical_sha(
                protocol.geometry_analytic_context_v2_payload(provisional)
            ),
        )
        return protocol.verify_geometry_analytic_context_v2(context)

    def _observer_spec(self):
        protocol = _protocol()
        provisional = protocol.ObserverCollapsePrerequisiteSpecV1(
            prerequisite_schema_version=(
                protocol.OBSERVER_COLLAPSE_PREREQUISITE_SPEC_V1_SCHEMA_VERSION
            ),
            formula_or_certificate_id=(
                protocol.OBSERVER_COLLAPSE_CONDITIONAL_FORMULA_ID
            ),
            claim_ceiling=protocol.OBSERVER_COLLAPSE_CONDITIONAL_CLAIM_CEILING,
            evaluation_state=protocol.OBSERVER_COLLAPSE_NOT_EVALUATED_STATE,
            required_predicate_ids=(protocol.OBSERVER_COLLAPSE_REQUIRED_PREDICATE_IDS),
            expected_incidence_rank=6,
            expected_tt_dimension=2,
            expected_gauge_dimension=4,
            expected_row_dimension=4,
            coisometry_residual_tolerance=1.0e-12,
            prerequisite_spec_sha="0" * 64,
        )
        spec = replace(
            provisional,
            prerequisite_spec_sha=canonical_sha(
                protocol.observer_collapse_prerequisite_spec_v1_payload(provisional)
            ),
        )
        return protocol.verify_observer_collapse_prerequisite_spec_v1(spec)

    def _bundle(
        self,
        kind: str,
        *,
        scenario_id: Optional[str] = None,
        selected_fejer_order: int = 256,
    ):
        protocol = _protocol()
        context = self._context(
            kind,
            scenario_id=scenario_id,
            selected_fejer_order=selected_fejer_order,
        )
        eye4 = np.eye(4, dtype=np.complex128)
        zero_optional = {
            "coverage_control_id": None,
            "coverage_control_wire": (),
            "undressed_response_representatives": None,
            "gauge_basis": None,
            "gauge_amplitude": None,
            "expected_graph_rank": None,
            "analytic_graph_singular_values": (),
            "fejer_graph_slope_formula_id": None,
            "expected_actual_raw_graph_singular_values": (),
            "expected_ablated_raw_graph_singular_values": (),
            "observer_collapse_spec": None,
        }

        if kind == protocol.C15_QUOTIENT_SPECTRUM:
            kernel = eye4[:, :3]
            quotient = eye4[:, (0, 1, 3)].conj().T
            metric = np.eye(3, dtype=np.complex128)
            targets = eye4[:, :2]
            zero_optional["gauge_basis"] = freeze_complex_tensor(eye4[:, 2:3])
        elif kind == protocol.C16_COVERAGE_CONTROL:
            kernel = eye4[:, :3]
            quotient = eye4[:, (0, 1, 3)].conj().T
            metric = np.eye(3, dtype=np.complex128)
            coverage = context.coverage_control
            self.assertIsNotNone(coverage)
            targets = (
                math.sqrt(coverage) * eye4[:, 0]
                + math.sqrt(1.0 - coverage) * eye4[:, 3]
            )[:, None]
            local_id = "00-coverage-low" if coverage == 0.25 else "01-coverage-high"
            zero_optional.update(
                coverage_control_id=(f"v3m0.synthetic-control.c16.v1.{local_id}"),
                coverage_control_wire=(coverage,),
            )
        elif kind == protocol.C17_QUOTIENT_GAUGE_GRAPH:
            eye6 = np.eye(6, dtype=np.complex128)
            undressed = eye6[:, :2]
            gauge = eye6[:, 2:4]
            kernel = np.column_stack((undressed, gauge))
            quotient = eye6[:, (0, 1, 4, 5)].conj().T
            metric = np.eye(4, dtype=np.complex128)
            targets = eye6[:, :2]
            expected_ablated = 8.0 * (1.0 / float(context.selected_fejer_order + 1))
            zero_optional.update(
                undressed_response_representatives=freeze_complex_tensor(undressed),
                gauge_basis=freeze_complex_tensor(gauge),
                gauge_amplitude=8.0,
                expected_graph_rank=2,
                analytic_graph_singular_values=(8.0, 8.0),
                fejer_graph_slope_formula_id=(
                    protocol.C17_FEJER_GRAPH_SLOPE_FORMULA_ID
                ),
                expected_actual_raw_graph_singular_values=(8.0, 8.0),
                expected_ablated_raw_graph_singular_values=(
                    expected_ablated,
                    expected_ablated,
                ),
            )
        elif kind == protocol.C18_INDEPENDENT_UNARY:
            kernel = eye4[:, :1]
            quotient = eye4
            metric = eye4
            targets = eye4[:, :2]
        else:
            kernel = eye4[:, :1]
            quotient = eye4
            metric = eye4
            targets = eye4[:, :2]
            zero_optional["observer_collapse_spec"] = self._observer_spec()

        provisional = protocol.ScenarioResponseGeometryBundleV3(
            geometry_bundle_schema_version=(
                protocol.SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V3_SCHEMA_VERSION
            ),
            geometry_kind=kind,
            analytic_context_sha=context.context_sha,
            scenario_id=context.scenario_id,
            scenario_sha=context.scenario_sha,
            recipe_sha=context.recipe_sha,
            geometry_derivation_source_id=(context.geometry_derivation_source_id),
            semantic_sector_names=context.semantic_sector_names,
            selected_fejer_order=context.selected_fejer_order,
            analytic_source_recipe_shas=context.analytic_source_recipe_shas,
            kernel_basis=freeze_complex_tensor(kernel),
            physical_quotient_map=freeze_complex_tensor(quotient),
            physical_quotient_metric=freeze_complex_tensor(metric),
            target_physical_representatives=freeze_complex_tensor(targets),
            **zero_optional,
            geometry_bundle_sha="0" * 64,
        )
        bundle = replace(
            provisional,
            geometry_bundle_sha=canonical_sha(
                protocol.scenario_response_geometry_bundle_v3_payload(provisional)
            ),
        )
        protocol.verify_scenario_response_geometry_bundle_v3(bundle)
        protocol.verify_scenario_response_geometry_bundle_v3_for_context(
            context,
            bundle,
        )
        return context, bundle

    def _resign_bundle(self, bundle, **changes):
        protocol = _protocol()
        provisional = replace(bundle, **changes, geometry_bundle_sha="0" * 64)
        return replace(
            provisional,
            geometry_bundle_sha=canonical_sha(
                protocol.scenario_response_geometry_bundle_v3_payload(provisional)
            ),
        )

    def _resign_context(self, context, **changes):
        protocol = _protocol()
        provisional = replace(context, **changes, context_sha="0" * 64)
        return replace(
            provisional,
            context_sha=canonical_sha(
                protocol.geometry_analytic_context_v2_payload(provisional)
            ),
        )

    def test_schema_constants_and_all_context_kinds_are_closed(self) -> None:
        protocol = _protocol()
        self.assertEqual(
            protocol.SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V3_SCHEMA_VERSION,
            "v3m0.scenario-response-geometry-bundle.v3",
        )
        self.assertEqual(len(protocol.GEOMETRY_KINDS_V3), 5)
        for kind in protocol.GEOMETRY_KINDS_V3:
            with self.subTest(kind=kind):
                self._context(kind)

    def test_canonical_payloads_cover_every_non_hash_field(self) -> None:
        protocol = _protocol()
        context, bundle = self._bundle(protocol.C19_OBSERVER_COLLAPSE_CONDITIONS)
        spec = bundle.observer_collapse_spec
        records = (
            (
                context,
                protocol.geometry_analytic_context_v2_payload(context),
                "context_sha",
            ),
            (
                spec,
                protocol.observer_collapse_prerequisite_spec_v1_payload(spec),
                "prerequisite_spec_sha",
            ),
            (
                bundle,
                protocol.scenario_response_geometry_bundle_v3_payload(bundle),
                "geometry_bundle_sha",
            ),
        )
        for record, payload, self_hash in records:
            with self.subTest(record=type(record).__name__):
                expected = {item.name for item in fields(record)} - {self_hash}
                self.assertEqual(set(payload), expected)

    def test_c16_reviewed_parent_derivation_id_is_the_only_valid_id(self) -> None:
        protocol = _protocol()
        context = self._context(protocol.C16_COVERAGE_CONTROL)
        self.assertEqual(
            context.geometry_derivation_source_id,
            "c16-analytic-coverage-target-bundle-v1",
        )
        with self.assertRaisesRegex(ValueError, "derivation"):
            replace(
                context,
                geometry_derivation_source_id=(
                    "c16-analytic-coverage-orientation-bundle-v1"
                ),
            )

    def test_c15_all_active_recipes_keep_their_canonical_scenario_slots(
        self,
    ) -> None:
        protocol = _protocol()
        scenarios = (
            "v3m0.synthetic-control.c15.v1.scenario.full-h.v1",
            "v3m0.synthetic-control.c15.v1.scenario.low-rank-tt.v1",
            "v3m0.synthetic-control.c15.v1.scenario.tt.v1",
            "v3m0.synthetic-control.c15.v1.scenario.tt-plus-row.v1",
        )
        for canonical_index, scenario_id in enumerate(scenarios):
            with self.subTest(scenario_id=scenario_id):
                context = self._context(
                    protocol.C15_QUOTIENT_SPECTRUM,
                    scenario_id=scenario_id,
                )
                self.assertEqual(
                    context.analytic_source_recipe_shas[canonical_index],
                    context.recipe_sha,
                )
                hostile_index = (canonical_index + 1) % len(scenarios)
                source_shas = list(context.analytic_source_recipe_shas)
                source_shas[canonical_index], source_shas[hostile_index] = (
                    source_shas[hostile_index],
                    source_shas[canonical_index],
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "canonical.*recipe|recipe.*slot",
                ):
                    self._resign_context(
                        context,
                        analytic_source_recipe_shas=tuple(source_shas),
                    )

    def test_c16_low_and_high_outputs_are_exact_and_cannot_be_crossed(self) -> None:
        protocol = _protocol()
        scenarios = (
            (
                "v3m0.synthetic-control.c16.v1.scenario.coverage-low.v1",
                ".00-coverage-low",
                0.25,
            ),
            (
                "v3m0.synthetic-control.c16.v1.scenario.coverage-high.v1",
                ".01-coverage-high",
                0.75,
            ),
        )
        for scenario_id, suffix, coverage in scenarios:
            with self.subTest(scenario_id=scenario_id):
                _, bundle = self._bundle(
                    protocol.C16_COVERAGE_CONTROL,
                    scenario_id=scenario_id,
                )
                self.assertTrue(bundle.coverage_control_id.endswith(suffix))
                self.assertEqual(bundle.coverage_control_wire, (coverage,))
                crossed_suffix = (
                    ".01-coverage-high"
                    if suffix == ".00-coverage-low"
                    else ".00-coverage-low"
                )
                crossed = self._resign_bundle(
                    bundle,
                    coverage_control_id=(
                        "v3m0.synthetic-control.c16.v1" + crossed_suffix
                    ),
                )
                with self.assertRaisesRegex(ValueError, "coverage control ID"):
                    protocol.verify_scenario_response_geometry_bundle_v3(crossed)
                wrong_instance = self._resign_bundle(
                    bundle,
                    coverage_control_id="forged.application" + suffix,
                )
                with self.assertRaisesRegex(ValueError, "coverage control ID"):
                    protocol.verify_scenario_response_geometry_bundle_v3(wrong_instance)

    def test_c15_preserves_tt_and_only_annihilates_gauge(self) -> None:
        protocol = _protocol()
        _, bundle = self._bundle(protocol.C15_QUOTIENT_SPECTRUM)
        quotient = frozen_tensor_array(bundle.physical_quotient_map)
        kernel = frozen_tensor_array(bundle.kernel_basis)
        gauge = frozen_tensor_array(bundle.gauge_basis)
        self.assertGreater(np.linalg.norm(quotient @ kernel, ord=2), 0.9)
        self.assertLessEqual(np.linalg.norm(quotient @ gauge, ord=2), 1.0e-15)

    def test_c17_preserves_tt_and_freezes_permit_t_formula(self) -> None:
        protocol = _protocol()
        _, bundle = self._bundle(protocol.C17_QUOTIENT_GAUGE_GRAPH)
        quotient = frozen_tensor_array(bundle.physical_quotient_map)
        undressed = frozen_tensor_array(bundle.undressed_response_representatives)
        gauge = frozen_tensor_array(bundle.gauge_basis)
        self.assertGreater(np.linalg.norm(quotient @ undressed, ord=2), 0.9)
        self.assertLessEqual(np.linalg.norm(quotient @ gauge, ord=2), 1.0e-15)
        expected = 8.0 / float(bundle.selected_fejer_order + 1)
        self.assertEqual(
            bundle.expected_ablated_raw_graph_singular_values,
            (expected, expected),
        )

    def test_c17_recomputes_the_formula_for_every_frozen_t(self) -> None:
        protocol = _protocol()
        for selected_fejer_order in protocol.CANDIDATE_FEJER_ORDERS:
            with self.subTest(selected_fejer_order=selected_fejer_order):
                _, bundle = self._bundle(
                    protocol.C17_QUOTIENT_GAUGE_GRAPH,
                    selected_fejer_order=selected_fejer_order,
                )
                expected = 8.0 * (1.0 / float(selected_fejer_order + 1))
                self.assertEqual(
                    bundle.expected_ablated_raw_graph_singular_values,
                    (expected, expected),
                )

    def test_c18_identity_quotient_is_valid_even_when_qk_is_nonzero(self) -> None:
        protocol = _protocol()
        _, bundle = self._bundle(protocol.C18_INDEPENDENT_UNARY)
        quotient = frozen_tensor_array(bundle.physical_quotient_map)
        kernel = frozen_tensor_array(bundle.kernel_basis)
        np.testing.assert_array_equal(quotient, np.eye(4, dtype=np.complex128))
        self.assertEqual(float(np.linalg.norm(quotient @ kernel)), 1.0)

    def test_c19_can_only_freeze_conditional_not_evaluated_prerequisites(
        self,
    ) -> None:
        protocol = _protocol()
        _, bundle = self._bundle(protocol.C19_OBSERVER_COLLAPSE_CONDITIONS)
        spec = bundle.observer_collapse_spec
        self.assertEqual(
            spec.claim_ceiling,
            "CONDITIONAL_PREREQUISITES_ONLY",
        )
        self.assertEqual(spec.evaluation_state, "NOT_EVALUATED_PRE_RESPONSE")
        for forged in ("TRIGGERED", "PASS"):
            with self.subTest(forged=forged):
                with self.assertRaisesRegex(ValueError, "evaluation"):
                    replace(spec, evaluation_state=forged)
        with self.assertRaisesRegex(ValueError, "claim ceiling"):
            replace(spec, claim_ceiling="PASS")

    def test_c19_prerequisite_schema_has_no_conclusion_slot(self) -> None:
        protocol = _protocol()
        spec = self._observer_spec()
        field_names = {item.name for item in fields(spec)}
        self.assertNotIn("predicted_outcome", field_names)
        self.assertNotIn("triggered", field_names)
        self.assertNotIn("verdict", field_names)
        for field_name, value in (("triggered", True), ("verdict", "PASS")):
            with self.subTest(field_name=field_name):
                hostile = replace(spec)
                object.__setattr__(hostile, field_name, value)
                with self.assertRaisesRegex(ValueError, "unknown or missing"):
                    protocol.verify_observer_collapse_prerequisite_spec_v1(hostile)

    def test_unknown_kind_and_missing_or_unknown_fields_are_rejected(self) -> None:
        protocol = _protocol()
        _, bundle = self._bundle(protocol.C18_INDEPENDENT_UNARY)
        with self.assertRaisesRegex(ValueError, "kind"):
            replace(bundle, geometry_kind="C99_UNKNOWN")

        missing = replace(bundle)
        object.__delattr__(missing, "recipe_sha")
        with self.assertRaisesRegex(ValueError, "unknown or missing"):
            protocol.verify_scenario_response_geometry_bundle_v3(missing)

        unknown = replace(bundle)
        object.__setattr__(unknown, "caller_verdict", "PASS")
        with self.assertRaisesRegex(ValueError, "unknown or missing"):
            protocol.verify_scenario_response_geometry_bundle_v3(unknown)

        class StringSubclass(str):
            pass

        with self.assertRaisesRegex(TypeError, "exact string"):
            replace(bundle, geometry_kind=StringSubclass(bundle.geometry_kind))

    def test_bundle_and_nested_prerequisite_self_hashes_are_enforced(self) -> None:
        protocol = _protocol()
        _, bundle = self._bundle(protocol.C19_OBSERVER_COLLAPSE_CONDITIONS)
        tampered = replace(bundle, scenario_sha=_sha(999))
        with self.assertRaisesRegex(ValueError, "SHA"):
            protocol.verify_scenario_response_geometry_bundle_v3(tampered)

        spec = bundle.observer_collapse_spec
        forged_spec = replace(spec, expected_incidence_rank=5)
        forged_bundle = self._resign_bundle(
            bundle,
            observer_collapse_spec=forged_spec,
        )
        with self.assertRaisesRegex(ValueError, "prerequisite|SHA"):
            protocol.verify_scenario_response_geometry_bundle_v3(forged_bundle)

    def test_context_and_nested_tensor_self_hashes_are_enforced(self) -> None:
        protocol = _protocol()
        context, bundle = self._bundle(protocol.C18_INDEPENDENT_UNARY)
        tampered_context = replace(context, scenario_sha=_sha(777))
        with self.assertRaisesRegex(ValueError, "context SHA"):
            protocol.verify_geometry_analytic_context_v2(tampered_context)

        tampered_kernel = replace(bundle.kernel_basis, tensor_sha=_sha(778))
        with self.assertRaisesRegex(ValueError, "tensor_sha"):
            self._resign_bundle(bundle, kernel_basis=tampered_kernel)

    def test_cross_kind_fields_are_rejected_after_resigning(self) -> None:
        protocol = _protocol()
        vector = freeze_complex_tensor(np.eye(4, dtype=np.complex128)[:, :1])
        cases = (
            (
                protocol.C15_QUOTIENT_SPECTRUM,
                {
                    "coverage_control_id": "forged.00-coverage-low",
                    "coverage_control_wire": (0.25,),
                },
            ),
            (
                protocol.C16_COVERAGE_CONTROL,
                {"observer_collapse_spec": self._observer_spec()},
            ),
            (
                protocol.C17_QUOTIENT_GAUGE_GRAPH,
                {
                    "coverage_control_id": "forged.00-coverage-low",
                    "coverage_control_wire": (0.25,),
                },
            ),
            (protocol.C18_INDEPENDENT_UNARY, {"gauge_basis": vector}),
            (
                protocol.C19_OBSERVER_COLLAPSE_CONDITIONS,
                {"undressed_response_representatives": vector},
            ),
        )
        for kind, changes in cases:
            with self.subTest(kind=kind):
                _, bundle = self._bundle(kind)
                hostile = self._resign_bundle(bundle, **changes)
                with self.assertRaisesRegex(ValueError, "cross-kind|C1[5-9]"):
                    protocol.verify_scenario_response_geometry_bundle_v3(hostile)

    def test_c15_rejects_a_quotient_that_annihilates_tt_with_gauge(self) -> None:
        protocol = _protocol()
        _, bundle = self._bundle(protocol.C15_QUOTIENT_SPECTRUM)
        quotient = np.zeros((1, 4), dtype=np.complex128)
        quotient[0, 3] = 1.0
        hostile = self._resign_bundle(
            bundle,
            physical_quotient_map=freeze_complex_tensor(quotient),
            physical_quotient_metric=freeze_complex_tensor(
                np.eye(1, dtype=np.complex128)
            ),
        )
        with self.assertRaisesRegex(ValueError, "preserve.*TT"):
            protocol.verify_scenario_response_geometry_bundle_v3(hostile)

    def test_c17_rejects_a_resigned_formula_or_tt_annihilating_quotient(
        self,
    ) -> None:
        protocol = _protocol()
        _, bundle = self._bundle(protocol.C17_QUOTIENT_GAUGE_GRAPH)
        wrong_formula = self._resign_bundle(
            bundle,
            expected_ablated_raw_graph_singular_values=(0.0, 0.0),
        )
        with self.assertRaisesRegex(ValueError, "Fejer|formula|slope"):
            protocol.verify_scenario_response_geometry_bundle_v3(wrong_formula)

        quotient = np.zeros((2, 6), dtype=np.complex128)
        quotient[0, 4] = 1.0
        quotient[1, 5] = 1.0
        kills_tt = self._resign_bundle(
            bundle,
            physical_quotient_map=freeze_complex_tensor(quotient),
            physical_quotient_metric=freeze_complex_tensor(
                np.eye(2, dtype=np.complex128)
            ),
        )
        with self.assertRaisesRegex(ValueError, "preserve.*TT"):
            protocol.verify_scenario_response_geometry_bundle_v3(kills_tt)

    def test_context_binding_rejects_a_resigned_cross_scenario_bundle(self) -> None:
        protocol = _protocol()
        context, bundle = self._bundle(protocol.C18_INDEPENDENT_UNARY)
        hostile = self._resign_bundle(bundle, scenario_sha=_sha(888))
        protocol.verify_scenario_response_geometry_bundle_v3(hostile)
        with self.assertRaisesRegex(ValueError, "context"):
            protocol.verify_scenario_response_geometry_bundle_v3_for_context(
                context,
                hostile,
            )


if __name__ == "__main__":
    unittest.main()
