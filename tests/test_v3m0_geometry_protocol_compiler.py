"""Adversarial tests for the repository-closed geometry v3 compiler."""

from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
import math
from types import SimpleNamespace
import unittest
from unittest import mock

import numpy as np

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor, frozen_tensor_array
from rulespace_v3 import geometry_protocol_compiler as compiler
from rulespace_v3 import geometry_protocol_v3 as protocol


def _sha(label: str) -> str:
    return hashlib.sha256(label.encode("utf-8")).hexdigest()


class _LiveParent:
    def __init__(self, body):
        self.body = body


class _LivePermit:
    def __init__(self, parent, body):
        self.parent = parent
        self.body = body


class _LiveMaterialization:
    def __init__(self, parent, permit, body):
        self.parent = parent
        self.permit = permit
        self.body = body


class _Fixture:
    def __init__(self, selected_t: int = 256):
        self.selected_t = selected_t
        self.rebuilds = {}
        self.scenarios = {}
        self.materialization_bodies = {}
        self.application_specs = []
        self._build_scenarios()
        applications = []
        for control_case, scenario_ids in self._case_scenarios().items():
            scenario_authorities = tuple(self.scenarios[item] for item in scenario_ids)
            application = SimpleNamespace(
                control_case_id=control_case,
                application_instance_id=scenario_ids[0].split(".scenario.", 1)[0],
                application_authority_sha=_sha(control_case + ".application"),
                scenario_authorities=scenario_authorities,
            )
            applications.append(application)
            candidate_scenarios = tuple(
                SimpleNamespace(
                    scenario_execution_spec=item.scenario_execution_spec,
                    response_template=SimpleNamespace(
                        geometry_bundle_derivation_id=(
                            protocol.GEOMETRY_DERIVATION_SOURCE_ID_BY_KIND[
                                self._kind(item.scenario_id)
                            ]
                            if item.scenario_id
                            not in compiler.C19_GEOMETRY_SCENARIO_IDS
                            else protocol.GEOMETRY_DERIVATION_SOURCE_ID_BY_KIND[
                                protocol.C19_OBSERVER_COLLAPSE_CONDITIONS
                            ]
                        )
                    ),
                )
                for item in scenario_authorities
            )
            self.application_specs.append(
                SimpleNamespace(scenario_candidates=candidate_scenarios)
            )
        parent_body = SimpleNamespace(
            parent_freeze_v2_sha=_sha("parent-v2"),
            current_application_authorities=tuple(applications),
            reviewed_candidate_v1=SimpleNamespace(
                application_candidates=tuple(self.application_specs)
            ),
            historical_parent_v1=SimpleNamespace(marker="historical-v1"),
        )
        self.parent = _LiveParent(parent_body)
        self.upstreams = {}
        for application in applications:
            permit_body = SimpleNamespace(
                parent_freeze_v2_sha=parent_body.parent_freeze_v2_sha,
                permit_sha=_sha(application.control_case_id + ".permit"),
                selected_fejer_order=selected_t,
                application_authority=application,
            )
            permit = _LivePermit(self.parent, permit_body)
            for scenario in application.scenario_authorities:
                body = self._materialization_body(
                    application,
                    scenario,
                    permit_body,
                )
                materialization = _LiveMaterialization(
                    self.parent,
                    permit,
                    body,
                )
                self.materialization_bodies[scenario.scenario_id] = body
                self.upstreams[scenario.scenario_id] = (permit, materialization)
        self.api = compiler._make_repository_closed_geometry_api(
            parent_type=_LiveParent,
            permit_type=_LivePermit,
            materialization_type=_LiveMaterialization,
            parent_reverifier=self._parent_reverifier,
            permit_parent_reverifier=self._permit_reverifier,
            materialization_upstream_reverifier=self._materialization_reverifier,
            analytic_rebuilder=self._analytic_rebuilder,
        )

    @staticmethod
    def _kind(scenario_id):
        if scenario_id in compiler.C15_GEOMETRY_SCENARIO_IDS:
            return protocol.C15_QUOTIENT_SPECTRUM
        if scenario_id in compiler.C16_GEOMETRY_SCENARIO_IDS:
            return protocol.C16_COVERAGE_CONTROL
        if scenario_id in compiler.C17_GEOMETRY_SCENARIO_IDS:
            return protocol.C17_QUOTIENT_GAUGE_GRAPH
        if scenario_id in compiler.C18_GEOMETRY_SCENARIO_IDS:
            return protocol.C18_INDEPENDENT_UNARY
        return protocol.C19_OBSERVER_COLLAPSE_CONDITIONS

    @staticmethod
    def _case_scenarios():
        return {
            "C15_TT_ROW_FULLH_LOWRANK_GEOMETRY": (compiler.C15_GEOMETRY_SCENARIO_IDS),
            "C16_COVERAGE_025_075": compiler.C16_GEOMETRY_SCENARIO_IDS,
            "C17_QUOTIENT_GAUGE_COVERAGE": compiler.C17_GEOMETRY_SCENARIO_IDS,
            "C18_ABLATED_INDEPENDENT_UNARY": compiler.C18_GEOMETRY_SCENARIO_IDS,
            "C19_FULL_POSITIVE_OBSERVER_COLLAPSE": (compiler.C19_GEOMETRY_SCENARIO_IDS),
        }

    def _build_scenarios(self):
        all_ids = tuple(
            identifier
            for scenario_ids in self._case_scenarios().values()
            for identifier in scenario_ids
        )
        for index, scenario_id in enumerate(all_ids):
            kind = self._kind(scenario_id)
            actual_rank, matched_rank = (
                (1, 2) if kind == protocol.C18_INDEPENDENT_UNARY else (2, 2)
            )
            output = self._output_id(scenario_id)
            execution = SimpleNamespace(
                scenario_id=scenario_id,
                scenario_sha=_sha(scenario_id + ".scenario"),
                operation_output_ids=(output,),
                recipe_derivation_source_id="signed-scenario-response-design-v1",
            )
            response = SimpleNamespace(
                response_contract_sha=_sha(scenario_id + ".response"),
                operation_dag_sha=_sha(scenario_id + ".dag"),
                compiled_contract_sha=_sha(scenario_id + ".contract"),
                preflight_derivation_or_recipe_sha=_sha(scenario_id + ".source"),
                expected_actual_shell_rank=actual_rank,
                expected_matched_shell_rank=matched_rank,
                uses_global_fft_projection=False,
                uses_per_k_time_step_projector=False,
            )
            self.scenarios[scenario_id] = SimpleNamespace(
                scenario_id=scenario_id,
                scenario_authority_sha=_sha(scenario_id + ".authority"),
                scenario_execution_spec=execution,
                response_contract=response,
            )
            if kind != protocol.C19_OBSERVER_COLLAPSE_CONDITIONS:
                self.rebuilds[scenario_id] = self._rebuild(
                    scenario_id,
                    kind,
                    response.preflight_derivation_or_recipe_sha,
                    execution.operation_output_ids,
                )

    @staticmethod
    def _output_id(scenario_id):
        application = scenario_id.split(".scenario.", 1)[0]
        if scenario_id.endswith("coverage-low.v1"):
            return application + ".00-coverage-low"
        if scenario_id.endswith("coverage-high.v1"):
            return application + ".01-coverage-high"
        return application + ".00-output"

    def _rebuild(self, scenario_id, kind, source_recipe_sha, output_ids):
        eye4 = np.eye(4, dtype=np.complex128)
        empty = dict(
            coverage_control_id=None,
            coverage_control_wire=(),
            undressed_response_representatives=None,
            gauge_basis=None,
            gauge_amplitude=None,
            expected_graph_rank=None,
            analytic_graph_singular_values=(),
            fejer_graph_slope_formula_id=None,
            expected_actual_raw_graph_singular_values=(),
            expected_ablated_raw_graph_singular_values=(),
        )
        if kind == protocol.C15_QUOTIENT_SPECTRUM:
            sectors_by_id = {
                compiler.C15_GEOMETRY_SCENARIO_IDS[0]: (
                    "TT0",
                    "TT1",
                    "Gauge",
                    "Row",
                ),
                compiler.C15_GEOMETRY_SCENARIO_IDS[1]: ("TT0",),
                compiler.C15_GEOMETRY_SCENARIO_IDS[2]: ("TT0", "TT1"),
                compiler.C15_GEOMETRY_SCENARIO_IDS[3]: ("TT0", "TT1", "Row"),
            }
            source_indices = {
                compiler.C15_GEOMETRY_SCENARIO_IDS[0]: (0, 1, 2, 3),
                compiler.C15_GEOMETRY_SCENARIO_IDS[1]: (0,),
                compiler.C15_GEOMETRY_SCENARIO_IDS[2]: (0, 1),
                compiler.C15_GEOMETRY_SCENARIO_IDS[3]: (0, 1, 3),
            }[scenario_id]
            source = eye4[:, source_indices]
            kernel = eye4[:, :3]
            quotient = eye4[:, (0, 1, 3)].conj().T
            metric = np.eye(3, dtype=np.complex128)
            targets = eye4[:, :2]
            empty["gauge_basis"] = freeze_complex_tensor(eye4[:, 2:3])
            sectors = sectors_by_id[scenario_id]
        elif kind == protocol.C16_COVERAGE_CONTROL:
            coverage = 0.25 if scenario_id.endswith("coverage-low.v1") else 0.75
            source = eye4[:, :1]
            kernel = eye4[:, :3]
            quotient = eye4[:, (0, 1, 3)].conj().T
            metric = np.eye(3, dtype=np.complex128)
            targets = (
                math.sqrt(coverage) * eye4[:, 0]
                + math.sqrt(1.0 - coverage) * eye4[:, 3]
            )[:, None]
            empty.update(
                coverage_control_id=output_ids[0],
                coverage_control_wire=(coverage,),
            )
            sectors = ("coverage-probe",)
        elif kind == protocol.C17_QUOTIENT_GAUGE_GRAPH:
            eye6 = np.eye(6, dtype=np.complex128)
            source = eye4[:, :2]
            undressed = eye6[:, :2]
            gauge = eye6[:, 2:4]
            kernel = np.column_stack((undressed, gauge))
            quotient = eye6[:, (0, 1, 4, 5)].conj().T
            metric = np.eye(4, dtype=np.complex128)
            targets = undressed
            ablated = 8.0 / float(self.selected_t + 1)
            empty.update(
                undressed_response_representatives=freeze_complex_tensor(undressed),
                gauge_basis=freeze_complex_tensor(gauge),
                gauge_amplitude=8.0,
                expected_graph_rank=2,
                analytic_graph_singular_values=(8.0, 8.0),
                fejer_graph_slope_formula_id=(
                    protocol.C17_FEJER_GRAPH_SLOPE_FORMULA_ID
                ),
                expected_actual_raw_graph_singular_values=(8.0, 8.0),
                expected_ablated_raw_graph_singular_values=(ablated, ablated),
            )
            sectors = ("dressed-coverage-probe-0", "dressed-coverage-probe-1")
        else:
            source = eye4[:, :2]
            kernel = eye4[:, :1]
            quotient = eye4
            metric = eye4
            targets = source
            sectors = ("actual-source-q0", "matched-new-source-q1")
        readout = eye4 if kind != protocol.C18_INDEPENDENT_UNARY else eye4[:2]
        return compiler._AnalyticGeometryRebuild(
            scenario_id=scenario_id,
            source_recipe_sha=source_recipe_sha,
            operation_output_ids=output_ids,
            semantic_sector_names=sectors,
            source_injection=freeze_complex_tensor(source),
            readout_coisometry=freeze_complex_tensor(readout),
            kernel_basis=freeze_complex_tensor(kernel),
            physical_quotient_map=freeze_complex_tensor(quotient),
            physical_quotient_metric=freeze_complex_tensor(metric),
            target_physical_representatives=freeze_complex_tensor(targets),
            **empty,
        )

    def _materialization_body(self, application, scenario, permit_body):
        rebuild = self.rebuilds.get(scenario.scenario_id)
        source = (
            rebuild.source_injection
            if rebuild is not None
            else freeze_complex_tensor(np.eye(4, dtype=np.complex128)[:, :2])
        )
        readout = (
            rebuild.readout_coisometry
            if rebuild is not None
            else freeze_complex_tensor(np.eye(4, dtype=np.complex128))
        )
        recipe = SimpleNamespace(
            scenario_id=scenario.scenario_id,
            scenario_sha=scenario.scenario_execution_spec.scenario_sha,
            operation_dag_sha=scenario.response_contract.operation_dag_sha,
            compiled_contract_sha=scenario.response_contract.compiled_contract_sha,
            recipe_sha=_sha(scenario.scenario_id + ".current-recipe"),
        )
        return SimpleNamespace(
            formal_parent_v2_sha=_sha("parent-v2"),
            permit_v2_sha=permit_body.permit_sha,
            selected_fejer_order=self.selected_t,
            application_authority_sha=application.application_authority_sha,
            control_case_id=application.control_case_id,
            application_instance_id=application.application_instance_id,
            scenario_id=scenario.scenario_id,
            scenario_sha=scenario.scenario_execution_spec.scenario_sha,
            scenario_authority_sha=scenario.scenario_authority_sha,
            response_contract_sha=scenario.response_contract.response_contract_sha,
            scenario_recipe=recipe,
            scenario_source_injection=source,
            scenario_readout_coisometry=readout,
            materialization_v2_sha=_sha(scenario.scenario_id + ".materialization"),
        )

    @staticmethod
    def _parent_reverifier(parent):
        if type(parent) is not _LiveParent:
            raise TypeError("not exact live parent")
        return parent.body

    @staticmethod
    def _permit_reverifier(permit, parent):
        if type(permit) is not _LivePermit or permit.parent is not parent:
            raise ValueError("permit is spliced from parent")
        return permit.body

    @staticmethod
    def _materialization_reverifier(parent, permit, materialization):
        if (
            type(materialization) is not _LiveMaterialization
            or materialization.parent is not parent
            or materialization.permit is not permit
        ):
            raise ValueError("materialization is spliced from upstream")
        return materialization.body

    def _analytic_rebuilder(self, parent_manifest, scenario_id, selected_t):
        if parent_manifest is not self.parent.body or selected_t != self.selected_t:
            raise ValueError("unexpected analytic rebuild upstream")
        return self.rebuilds[scenario_id]

    @property
    def c15_references(self):
        return tuple(
            self.upstreams[item] for item in compiler.C15_GEOMETRY_SCENARIO_IDS
        )

    @property
    def ordered_upstreams(self):
        return tuple(
            self.upstreams[item]
            for item in compiler.CANONICAL_GEOMETRY_PRODUCTION_SCENARIO_IDS
        )

    def compile(self, scenario_id):
        compile_one, _, _ = self.api
        permit, materialization = self.upstreams[scenario_id]
        return compile_one(
            self.parent,
            permit,
            materialization,
            c15_reference_upstreams=(
                self.c15_references
                if scenario_id
                in (
                    *compiler.C15_GEOMETRY_SCENARIO_IDS,
                    *compiler.C16_GEOMETRY_SCENARIO_IDS,
                )
                else ()
            ),
        )


class GeometryProtocolCompilerPositiveTests(unittest.TestCase):
    def test_batch_compiles_exactly_eight_c15_through_c18_scenarios(self):
        fixture = _Fixture()
        _, _, compile_batch = fixture.api
        results = compile_batch(fixture.parent, fixture.ordered_upstreams)
        self.assertEqual(
            tuple(item.analytic_context.scenario_id for item in results),
            compiler.CANONICAL_GEOMETRY_PRODUCTION_SCENARIO_IDS,
        )
        self.assertTrue(
            all(
                item.authority_state
                == compiler.REPOSITORY_CLOSED_GEOMETRY_COMPILATION_AUTHORITY_STATE
                and item.response_evidence_state == "NOT_RUN_PRE_RESPONSE"
                and item.scientific_verdict_state == "NOT_EVALUATED"
                for item in results
            )
        )
        for item in results[:4]:
            self.assertEqual(
                item.analytic_context.analytic_source_recipe_shas,
                tuple(
                    fixture.materialization_bodies[
                        scenario_id
                    ].scenario_recipe.recipe_sha
                    for scenario_id in compiler.C15_GEOMETRY_SCENARIO_IDS
                ),
            )
        for item in results[4:6]:
            self.assertEqual(len(item.c15_reference_compilation_shas), 4)
            self.assertEqual(
                item.analytic_context.analytic_source_recipe_shas[:4],
                results[0].analytic_context.analytic_source_recipe_shas,
            )

    def test_c16_exact_output_and_target_are_repository_rebuilt(self):
        fixture = _Fixture()
        low = fixture.compile(compiler.C16_GEOMETRY_SCENARIO_IDS[0])
        high = fixture.compile(compiler.C16_GEOMETRY_SCENARIO_IDS[1])
        self.assertTrue(
            low.geometry_bundle.coverage_control_id.endswith(".00-coverage-low")
        )
        self.assertTrue(
            high.geometry_bundle.coverage_control_id.endswith(".01-coverage-high")
        )
        self.assertEqual(low.geometry_bundle.coverage_control_wire, (0.25,))
        self.assertEqual(high.geometry_bundle.coverage_control_wire, (0.75,))
        self.assertFalse(
            np.array_equal(
                frozen_tensor_array(
                    low.geometry_bundle.target_physical_representatives
                ),
                frozen_tensor_array(
                    high.geometry_bundle.target_physical_representatives
                ),
            )
        )

    def test_c17_recomputes_graph_wire_for_all_six_permit_orders(self):
        for selected_t in protocol.CANDIDATE_FEJER_ORDERS:
            with self.subTest(selected_t=selected_t):
                fixture = _Fixture(selected_t)
                result = fixture.compile(compiler.C17_GEOMETRY_SCENARIO_IDS[0])
                expected = 8.0 / float(selected_t + 1)
                self.assertEqual(result.geometry_bundle.gauge_amplitude, 8.0)
                self.assertEqual(result.geometry_bundle.expected_graph_rank, 2)
                self.assertEqual(
                    result.geometry_bundle.expected_ablated_raw_graph_singular_values,
                    (expected, expected),
                )

    def test_c18_compiles_actual_and_new_directions_with_identity_q_and_m(self):
        fixture = _Fixture()
        result = fixture.compile(compiler.C18_GEOMETRY_SCENARIO_IDS[0])
        bundle = result.geometry_bundle
        self.assertTrue(
            np.array_equal(
                frozen_tensor_array(bundle.physical_quotient_map),
                np.eye(4),
            )
        )
        self.assertTrue(
            np.array_equal(
                frozen_tensor_array(bundle.physical_quotient_metric),
                np.eye(4),
            )
        )
        self.assertGreater(
            np.linalg.norm(
                frozen_tensor_array(bundle.physical_quotient_map)
                @ frozen_tensor_array(bundle.kernel_basis)
            ),
            0.9,
        )


class GeometryProtocolCompilerAdversarialTests(unittest.TestCase):
    def test_public_surface_accepts_no_caller_matrix_threshold_or_t(self):
        parameters = inspect.signature(
            compiler.compile_repository_closed_geometry_v1
        ).parameters
        self.assertEqual(
            tuple(parameters),
            (
                "formal_parent_v2",
                "permit_v2",
                "materialization_v2",
                "c15_reference_upstreams",
            ),
        )
        with self.assertRaises(TypeError):
            compiler.compile_repository_closed_geometry_v1(
                object(),
                object(),
                object(),
                kernel_basis=np.eye(4),
            )

    def test_splicing_subclass_and_fake_wrappers_are_rejected(self):
        fixture = _Fixture()
        compile_one, _, _ = fixture.api
        scenario_id = compiler.C17_GEOMETRY_SCENARIO_IDS[0]
        permit, materialization = fixture.upstreams[scenario_id]
        foreign_parent = _LiveParent(fixture.parent.body)
        with self.assertRaisesRegex(ValueError, "spliced"):
            compile_one(foreign_parent, permit, materialization)

        class HostilePermit(_LivePermit):
            pass

        hostile = HostilePermit(fixture.parent, permit.body)
        with self.assertRaisesRegex(TypeError, "exact live permit"):
            compile_one(fixture.parent, hostile, materialization)

    def test_c15_reference_order_and_operation_output_splices_fail_closed(self):
        fixture = _Fixture()
        compile_one, _, _ = fixture.api
        permit, materialization = fixture.upstreams[
            compiler.C16_GEOMETRY_SCENARIO_IDS[0]
        ]
        with self.assertRaisesRegex(ValueError, "canonical scenario order"):
            compile_one(
                fixture.parent,
                permit,
                materialization,
                c15_reference_upstreams=tuple(reversed(fixture.c15_references)),
            )
        scenario_id = compiler.C16_GEOMETRY_SCENARIO_IDS[0]
        original = fixture.rebuilds[scenario_id]
        fixture.rebuilds[scenario_id] = replace(
            original,
            operation_output_ids=("forged.00-coverage-low",),
        )
        with self.assertRaisesRegex(ValueError, "analytic rebuild"):
            fixture.compile(scenario_id)

    def test_full_resign_of_wrong_c16_target_cannot_pass_live_replay(self):
        fixture = _Fixture()
        result = fixture.compile(compiler.C16_GEOMETRY_SCENARIO_IDS[0])
        bundle0 = replace(
            result.geometry_bundle,
            target_physical_representatives=freeze_complex_tensor(
                np.eye(4, dtype=np.complex128)[:, 1:2]
            ),
            geometry_bundle_sha="0" * 64,
        )
        bundle = replace(
            bundle0,
            geometry_bundle_sha=canonical_sha(
                protocol.scenario_response_geometry_bundle_v3_payload(bundle0)
            ),
        )
        compilation0 = replace(
            result,
            geometry_bundle=bundle,
            compilation_sha="0" * 64,
        )
        attacked = replace(
            compilation0,
            compilation_sha=canonical_sha(
                compiler.repository_closed_geometry_compilation_v1_payload(compilation0)
            ),
        )
        _, verify, _ = fixture.api
        permit, materialization = fixture.upstreams[
            compiler.C16_GEOMETRY_SCENARIO_IDS[0]
        ]
        with self.assertRaisesRegex(ValueError, "closed live replay"):
            verify(
                fixture.parent,
                permit,
                materialization,
                attacked,
                c15_reference_upstreams=fixture.c15_references,
            )

    def test_module_rebinding_does_not_replace_captured_public_graph(self):
        fixture = _Fixture()
        scenario_id = compiler.C16_GEOMETRY_SCENARIO_IDS[0]
        poison = mock.Mock(side_effect=AssertionError("module rebind consumed"))
        with (
            mock.patch.object(
                compiler,
                "_compile_resolved_geometry",
                poison,
            ),
            mock.patch.object(
                compiler,
                "_production_analytic_rebuilder",
                poison,
            ),
            mock.patch.object(
                compiler,
                "_validate_upstream_tuple",
                poison,
            ),
            mock.patch.object(
                compiler,
                "_build_context_and_bundle",
                poison,
            ),
            mock.patch.object(
                compiler,
                "_validate_lineage",
                poison,
            ),
            mock.patch.object(
                compiler,
                "_validate_c15_references",
                poison,
            ),
            mock.patch.object(
                compiler,
                "_verify_compilation_body",
                poison,
            ),
            mock.patch.object(
                compiler,
                "canonical_sha",
                poison,
            ),
            mock.patch.object(
                compiler,
                "GEOMETRY_SCIENTIFIC_VERDICT_STATE",
                "PASS",
            ),
            mock.patch.object(
                compiler,
                "REPOSITORY_CLOSED_GEOMETRY_COMPILATION_AUTHORITY_STATE",
                "ISSUED",
            ),
        ):
            result = fixture.compile(scenario_id)
        self.assertEqual(result.geometry_kind, protocol.C16_COVERAGE_CONTROL)
        poison.assert_not_called()

    def test_c19_is_explicitly_not_evaluated_and_cannot_compile_a_fake_pass(self):
        fixture = _Fixture()
        compile_one, _, _ = fixture.api
        permit, materialization = fixture.upstreams[
            compiler.C19_GEOMETRY_SCENARIO_IDS[0]
        ]
        with self.assertRaisesRegex(
            compiler.GeometryProductionCompilationUnavailable,
            "10D|NOT_EVALUATED",
        ):
            compile_one(fixture.parent, permit, materialization)
        c18 = fixture.compile(compiler.C18_GEOMETRY_SCENARIO_IDS[0])
        with self.assertRaisesRegex(ValueError, "scientific verdict"):
            replace(c18, scientific_verdict_state="PASS")

    def test_raw_fixture_output_has_no_hydration_or_authority_promotion_path(self):
        fixture = _Fixture()
        raw = fixture.compile(compiler.C18_GEOMETRY_SCENARIO_IDS[0])
        self.assertIs(type(raw), compiler.RepositoryClosedGeometryCompilationV1)
        for name in ("hydrate", "issue", "authority", "capability"):
            self.assertFalse(hasattr(type(raw), name))
        attacked = replace(raw)
        object.__setattr__(attacked, "authority_token", object())
        with self.assertRaisesRegex(ValueError, "unknown or missing"):
            compiler._verify_compilation_body(attacked)

    def test_real_public_api_rejects_raw_and_forged_upstream_objects(self):
        from rulespace_v3.application_authority_v2 import (
            VerifiedCalibrationApplicationPermitV2,
        )
        from rulespace_v3.application_materialization_v2 import (
            VerifiedV3M0ApplicationScenarioMaterializationV2,
        )
        from rulespace_v3.parent_authority import VerifiedParentFreezeV2

        values = (
            (object(), object(), object()),
            (
                object.__new__(VerifiedParentFreezeV2),
                object.__new__(VerifiedCalibrationApplicationPermitV2),
                object.__new__(VerifiedV3M0ApplicationScenarioMaterializationV2),
            ),
        )
        for parent, permit, materialization in values:
            with self.subTest(parent=type(parent).__name__):
                with self.assertRaises((TypeError, ValueError)):
                    compiler.compile_repository_closed_geometry_v1(
                        parent,
                        permit,
                        materialization,
                    )


if __name__ == "__main__":
    unittest.main()
