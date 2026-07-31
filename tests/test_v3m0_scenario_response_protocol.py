"""Exact-contract tests for the pre-response scenario protocol v2.

Raw records are deliberately authority-neutral.  The public issuer is closed
over the future live Parent-v2/permit-v2/materialization-v2 chain and therefore
must fail closed while the latter two authorities do not exist.
"""

from __future__ import annotations

import copy
import inspect
import math
from dataclasses import fields, replace
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import numpy as np


SHA = "a" * 64


class ScenarioResponseProtocolContractTests(unittest.TestCase):
    @classmethod
    def _historical_parent(cls):
        from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze

        cached = getattr(cls, "_historical_parent_cache", None)
        if cached is None:
            cached = issue_v3m0_parent_freeze().manifest
            cls._historical_parent_cache = cached
        return cached

    @classmethod
    def _historical_application(cls, control_case_id):
        applications = tuple(
            item
            for item in cls._historical_parent().synthetic_control_application_specs
            if item.control_case_id == control_case_id
        )
        if len(applications) != 1:
            raise AssertionError("test fixture did not resolve one historical application")
        return applications[0]

    def _upstream_bodies(self, protocol):
        response_contract = SimpleNamespace(
            scenario_id=protocol.scenario_id,
            response_contract_sha="6" * 64,
            operation_dag_sha=protocol.operation_dag_sha,
            compiled_contract_sha=protocol.compiled_contract_sha,
            selector_spec=SimpleNamespace(
                source_selector=protocol.source_selector,
                readout_selector=protocol.readout_selector,
                source_injection=protocol.source_injection_isometry,
                readout_coisometry=protocol.readout_coisometry,
            ),
            source_trial_vectors=protocol.source_trial_vectors,
            response_torus_denominators=protocol.response_torus_denominators,
            response_reciprocal_indices=protocol.response_reciprocal_indices,
            source_readout_bridge_reciprocal_indices=(
                protocol.source_bridge_reciprocal_indices
            ),
            source_readout_bridge_steps=protocol.source_readout_bridge_steps,
            reference_reciprocal_index=protocol.reference_reciprocal_index,
            preregistered_phase_bands=tuple(
                item.phase_band for item in protocol.momentum_wires
            ),
            expected_actual_shell_rank=(
                protocol.momentum_wires[0].expected_actual_shell_rank
            ),
            expected_matched_shell_rank=(
                protocol.momentum_wires[0].expected_matched_shell_rank
            ),
        )
        scenario_authority = SimpleNamespace(
            scenario_id=protocol.scenario_id,
            scenario_authority_sha="5" * 64,
            scenario_execution_spec=SimpleNamespace(
                scenario_id=protocol.scenario_id,
                scenario_sha=protocol.scenario_sha,
                execution_lane="BLOCK_SUCCESS",
            ),
            response_contract=response_contract,
        )
        application_authority = SimpleNamespace(
            control_case_id=protocol.control_case_id,
            application_instance_id=protocol.application_instance_id,
            based_on_application_spec_sha=protocol.application_spec_sha,
            application_authority_sha="4" * 64,
            scenario_authorities=(scenario_authority,),
        )
        parent = SimpleNamespace(
            parent_freeze_v2_sha=protocol.formal_parent_v2_sha,
            historical_parent_v1=self._historical_parent(),
            current_application_authorities=(application_authority,),
        )
        permit = SimpleNamespace(
            parent_freeze_v2_sha=protocol.formal_parent_v2_sha,
            permit_sha=protocol.permit_v2_sha,
            control_case_id=protocol.control_case_id,
            application_authority=application_authority,
            scenario_authority_shas=(scenario_authority.scenario_authority_sha,),
            selected_fejer_order=protocol.selected_fejer_order,
        )
        recipe = SimpleNamespace(
            formal_parent_v2_sha=protocol.formal_parent_v2_sha,
            permit_v2_sha=protocol.permit_v2_sha,
            application_spec_sha=protocol.application_spec_sha,
            scenario_authority_sha=scenario_authority.scenario_authority_sha,
            response_contract_sha=response_contract.response_contract_sha,
            control_case_id=protocol.control_case_id,
            application_instance_id=protocol.application_instance_id,
            scenario_id=protocol.scenario_id,
            scenario_sha=protocol.scenario_sha,
            operation_dag_sha=protocol.operation_dag_sha,
            compiled_contract_sha=protocol.compiled_contract_sha,
            source_selector=protocol.source_selector,
            readout_selector=protocol.readout_selector,
            recipe_sha=protocol.recipe_sha,
            actual_effect=SimpleNamespace(
                effect_digest=protocol.actual_effect_digest,
            ),
            matched_ablated_effect=SimpleNamespace(
                effect_digest=protocol.matched_ablated_effect_digest,
            ),
        )
        trace = SimpleNamespace(
            scenario_id=protocol.scenario_id,
            scenario_sha=protocol.scenario_sha,
            recipe_sha=protocol.recipe_sha,
            operation_dag_sha=protocol.operation_dag_sha,
            compiled_contract_sha=protocol.compiled_contract_sha,
            state_schema_id=protocol.state_schema_id,
            channel_order=protocol.channel_order,
            state_shape=(len(protocol.channel_order), *protocol.spatial_shape),
            construction_trace_sha=protocol.construction_trace_sha,
            actual_effect_digest=protocol.actual_effect_digest,
            matched_ablated_effect_digest=protocol.matched_ablated_effect_digest,
        )
        actual_binding = SimpleNamespace(
            branch="actual",
            scenario_id=protocol.scenario_id,
            scenario_sha=protocol.scenario_sha,
            recipe_sha=protocol.recipe_sha,
            construction_trace_sha=protocol.construction_trace_sha,
            effect_digest=protocol.actual_effect_digest,
            factory_sha=protocol.actual_factory_sha,
        )
        matched_binding = SimpleNamespace(
            branch="matched_ablated",
            scenario_id=protocol.scenario_id,
            scenario_sha=protocol.scenario_sha,
            recipe_sha=protocol.recipe_sha,
            construction_trace_sha=protocol.construction_trace_sha,
            effect_digest=protocol.matched_ablated_effect_digest,
            factory_sha=protocol.matched_ablated_factory_sha,
        )
        materialization = SimpleNamespace(
            formal_parent_v2_sha=protocol.formal_parent_v2_sha,
            permit_v2_sha=protocol.permit_v2_sha,
            application_authority_sha=application_authority.application_authority_sha,
            application_spec_sha=protocol.application_spec_sha,
            control_case_id=protocol.control_case_id,
            application_instance_id=protocol.application_instance_id,
            scenario_authority_sha=scenario_authority.scenario_authority_sha,
            response_contract_sha=response_contract.response_contract_sha,
            scenario_id=protocol.scenario_id,
            scenario_sha=protocol.scenario_sha,
            selected_fejer_order=protocol.selected_fejer_order,
            common_source_basis=protocol.common_source_basis,
            common_readout_basis=protocol.common_readout_basis,
            scenario_recipe=recipe,
            scenario_source_injection=protocol.source_injection_isometry,
            scenario_readout_coisometry=protocol.readout_coisometry,
            construction_trace=trace,
            actual_factory_binding=actual_binding,
            matched_ablated_factory_binding=matched_binding,
            materialization_v2_sha=protocol.materialization_v2_sha,
        )
        return parent, permit, materialization

    def _expected_inputs(self, protocol, parent, permit, materialization):
        from rulespace_v3.scenario_response_protocol import (
            _build_expected_scenario_protocol_inputs,
        )

        return _build_expected_scenario_protocol_inputs(
            parent,
            permit,
            materialization,
            momentum_wires=protocol.momentum_wires,
            geometry_bundle=protocol.geometry_bundle,
        )

    def _resign_momentum(self, momentum):
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.scenario_response_protocol import (
            scenario_response_momentum_wire_v2_payload,
        )

        provisional = replace(momentum, momentum_wire_sha="0" * 64)
        return replace(
            provisional,
            momentum_wire_sha=canonical_sha(
                scenario_response_momentum_wire_v2_payload(provisional)
            ),
        )

    def _resign_geometry(self, geometry):
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.scenario_response_protocol import (
            scenario_response_geometry_bundle_v2_payload,
        )

        provisional = replace(geometry, geometry_bundle_sha="0" * 64)
        return replace(
            provisional,
            geometry_bundle_sha=canonical_sha(
                scenario_response_geometry_bundle_v2_payload(provisional)
            ),
        )

    def _resign_protocol(self, protocol):
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.scenario_response_protocol import (
            application_scenario_response_protocol_v2_payload,
        )

        provisional = replace(protocol, protocol_sha="0" * 64)
        return replace(
            provisional,
            protocol_sha=canonical_sha(
                application_scenario_response_protocol_v2_payload(provisional)
            ),
        )

    def _protocol(self, *, laplacian: bool = False, geometry: bool = True):
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.factory import (
            basis_manifest_array,
            build_basis_manifest,
            freeze_complex_tensor,
            frozen_tensor_array,
        )
        from rulespace_v3.grids import (
            build_application_bridge_grid_manifest,
            build_response_grid_manifest,
        )
        from rulespace_v3.scenario_response_protocol import (
            APPLICATION_SCENARIO_RESPONSE_PROTOCOL_V2_SCHEMA_VERSION,
            SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V2_SCHEMA_VERSION,
            SCENARIO_RESPONSE_MOMENTUM_WIRE_V2_SCHEMA_VERSION,
            ApplicationScenarioResponseProtocolV2,
            ScenarioResponseGeometryBundleV2,
            ScenarioResponseMomentumWireV2,
            scenario_response_geometry_bundle_v2_payload,
            scenario_response_momentum_wire_v2_payload,
        )

        control_case_id = (
            "C12_NU_INC_IR_NORMALIZATION"
            if laplacian
            else ("C15" if geometry else "C04")
        )
        control_slug = control_case_id.lower()
        scenario_id = (
            f"v3m0.calibration.{control_slug}.application.main.scenario.response.v2"
        )
        scenario_sha = "2" * 64
        recipe_sha = "3" * 64
        if laplacian:
            application = self._historical_application(control_case_id)
            common_source = application.basis_protocol.source_basis
            common_readout = application.basis_protocol.readout_basis
            channels = common_source.channel_order
            state_schema_id = common_source.state_schema_id
            source_selector_values = np.asarray(
                (
                    (1.0, 0.0),
                    (0.0, 1.0),
                    (0.0, 0.0),
                    (0.0, 0.0),
                ),
                dtype=np.complex128,
            )
            readout_selector_values = np.asarray(
                (
                    (1.0, 0.0, 0.0, 0.0),
                    (0.0, 1.0, 0.0, 0.0),
                ),
                dtype=np.complex128,
            )
            grid = application.grid_protocol
            response_grid = build_response_grid_manifest(application)
            bridge_grid = build_application_bridge_grid_manifest(application)
            spatial_shape = grid.spatial_shape
            denominators = grid.response_torus_denominators
            reciprocal_indices = grid.response_reciprocal_indices
            bridge_indices = grid.bridge_reciprocal_indices
            bridge_steps = grid.bridge_steps
            reference_index = grid.reference_reciprocal_index
            phase_band = grid.preregistered_phase_bands[0]
            expected_rank = grid.expected_shell_rank
            application_spec_sha = application.application_spec_sha
            application_instance_id = application.application_instance_id
            response_grid_sha = response_grid.response_grid_sha
            bridge_grid_sha = bridge_grid.bridge_grid_sha
            common_incidence = frozen_tensor_array(
                application.readout_protocol.curvature_incidence_operator
            )
            normalized_incidence = (
                common_incidence @ readout_selector_values.conj().T
            )
            source_metric_whitener = freeze_complex_tensor(
                np.eye(source_selector_values.shape[1], dtype=np.complex128)
            )
            h_metric_whitener = freeze_complex_tensor(
                np.eye(readout_selector_values.shape[0], dtype=np.complex128)
            )
            curvature_metric_whitener = (
                application.readout_protocol.curvature_metric_whitener
            )
        else:
            channels = ("q", "p")
            state_schema_id = "v3m0.test.state.v1"
            common_source = build_basis_manifest(
                role="source",
                state_schema_id=state_schema_id,
                channel_order=channels,
                vectors=np.eye(2, dtype=np.complex128),
            )
            common_readout = build_basis_manifest(
                role="readout",
                state_schema_id=state_schema_id,
                channel_order=channels,
                vectors=np.asarray(
                    ((1j, 0.0), (0.0, 1.0)), dtype=np.complex128
                ),
            )
            source_selector_values = np.asarray(
                ((1.0,), (0.0,)), dtype=np.complex128
            )
            readout_selector_values = np.asarray(
                ((1.0, 0.0),), dtype=np.complex128
            )
            spatial_shape = (8, 8)
            denominators = (8, 8)
            reciprocal_indices = ((1, 0),)
            bridge_indices = ((1, 0),)
            bridge_steps = (4,)
            reference_index = (1, 0)
            phase_band = (0.2, 0.4)
            expected_rank = 1
            application_spec_sha = SHA
            application_instance_id = (
                f"v3m0.calibration.{control_slug}.application.main.v2"
            )
            response_grid_sha = "e" * 64
            bridge_grid_sha = "f" * 64
            normalized_incidence = np.eye(1, dtype=np.complex128)
            identity = freeze_complex_tensor(np.eye(1, dtype=np.complex128))
            source_metric_whitener = identity
            h_metric_whitener = identity
            curvature_metric_whitener = identity

        source_injection_values = (
            basis_manifest_array(common_source).T @ source_selector_values
        )
        readout_values = readout_selector_values @ np.conjugate(
            basis_manifest_array(common_readout)
        )
        momentum_wires = []
        for reciprocal_index in reciprocal_indices:
            momentum_values = tuple(
                2.0
                * math.pi
                * (index if index <= denominator // 2 else index - denominator)
                / denominator
                for index, denominator in zip(reciprocal_index, denominators)
            )
            if laplacian:
                normalizer = float(
                    4.0
                    * sum(
                        np.sin(np.float64(value) / np.float64(2.0)) ** 2
                        for value in momentum_values
                    )
                )
                incidence_family = "synthetic-lattice-laplacian-incidence-v1"
                normalizer_formula = "nu-inc-4-sum-sin2-half-v1"
                derivation = (
                    "2-exp(+ik)-exp(-ik)-centered-second-difference-v1"
                )
                incidence_values = normalizer * normalized_incidence
            else:
                normalizer = 1.0
                incidence_family = "identity-incidence-v1"
                normalizer_formula = "identity-positive-normalizer-v1"
                derivation = "identity-incidence-derivation-v1"
                incidence_values = normalized_incidence
            momentum = ScenarioResponseMomentumWireV2(
                momentum_wire_schema_version=(
                    SCENARIO_RESPONSE_MOMENTUM_WIRE_V2_SCHEMA_VERSION
                ),
                scenario_id=scenario_id,
                reciprocal_index=reciprocal_index,
                momentum_wire=momentum_values,
                phase_band=phase_band,
                expected_actual_shell_rank=expected_rank,
                expected_matched_shell_rank=expected_rank,
                curvature_incidence_family_id=incidence_family,
                curvature_incidence_operator=freeze_complex_tensor(
                    incidence_values
                ),
                curvature_normalizer_formula_id=normalizer_formula,
                curvature_normalizer_derivation_id=derivation,
                curvature_normalizer_value=normalizer,
                normalized_curvature_incidence_operator=freeze_complex_tensor(
                    incidence_values / np.float64(normalizer)
                ),
                curvature_ir_limit_formula_id=(
                    "normalized-incidence-ir-limit-v1"
                ),
                curvature_ir_certificate_sha="4" * 64,
                momentum_wire_sha="0" * 64,
            )
            momentum_wires.append(
                replace(
                    momentum,
                    momentum_wire_sha=canonical_sha(
                        scenario_response_momentum_wire_v2_payload(momentum)
                    ),
                )
            )

        geometry_bundle = None
        if geometry:
            geometry_bundle = ScenarioResponseGeometryBundleV2(
                geometry_bundle_schema_version=(
                    SCENARIO_RESPONSE_GEOMETRY_BUNDLE_V2_SCHEMA_VERSION
                ),
                geometry_kind="C15_QUOTIENT_SPECTRUM",
                scenario_id=scenario_id,
                scenario_sha=scenario_sha,
                recipe_sha=recipe_sha,
                kernel_basis=freeze_complex_tensor(
                    np.asarray(((0.0,), (1.0,)), dtype=np.complex128)
                ),
                physical_quotient_map=freeze_complex_tensor(
                    np.asarray(((1.0, 0.0),), dtype=np.complex128)
                ),
                physical_quotient_metric=freeze_complex_tensor(
                    np.eye(1, dtype=np.complex128)
                ),
                target_physical_representatives=freeze_complex_tensor(
                    np.asarray(((1.0,), (0.0,)), dtype=np.complex128)
                ),
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
                geometry_bundle_sha="0" * 64,
            )
            geometry_bundle = replace(
                geometry_bundle,
                geometry_bundle_sha=canonical_sha(
                    scenario_response_geometry_bundle_v2_payload(geometry_bundle)
                ),
            )

        source_trials = freeze_complex_tensor(
            np.eye(source_selector_values.shape[1], dtype=np.complex128)
        )
        protocol = ApplicationScenarioResponseProtocolV2(
            protocol_schema_version=(
                APPLICATION_SCENARIO_RESPONSE_PROTOCOL_V2_SCHEMA_VERSION
            ),
            protocol_state="FORMAL_PARENT_V2_BOUND_PRE_RESPONSE",
            formal_parent_v2_sha="0" * 64,
            permit_v2_sha="1" * 64,
            application_spec_sha=application_spec_sha,
            application_instance_id=application_instance_id,
            control_case_id=control_case_id,
            scenario_id=scenario_id,
            scenario_sha=scenario_sha,
            operation_dag_sha="5" * 64,
            compiled_contract_sha="6" * 64,
            materialization_v2_sha="7" * 64,
            recipe_sha=recipe_sha,
            construction_trace_sha="8" * 64,
            actual_factory_sha="9" * 64,
            matched_ablated_factory_sha="b" * 64,
            actual_effect_digest="c" * 64,
            matched_ablated_effect_digest="d" * 64,
            selected_fejer_order=16,
            common_source_basis=common_source,
            common_readout_basis=common_readout,
            source_selector=freeze_complex_tensor(source_selector_values),
            readout_selector=freeze_complex_tensor(readout_selector_values),
            source_injection_isometry=freeze_complex_tensor(
                source_injection_values
            ),
            readout_coisometry=freeze_complex_tensor(readout_values),
            state_schema_id=state_schema_id,
            channel_order=channels,
            spatial_shape=spatial_shape,
            response_torus_denominators=denominators,
            response_reciprocal_indices=reciprocal_indices,
            response_grid_sha=response_grid_sha,
            source_bridge_reciprocal_indices=bridge_indices,
            source_bridge_grid_sha=bridge_grid_sha,
            readout_bridge_reciprocal_indices=bridge_indices,
            readout_bridge_grid_sha=bridge_grid_sha,
            source_readout_bridge_steps=bridge_steps,
            reference_reciprocal_index=reference_index,
            source_trial_vectors=source_trials,
            bridge_tolerance=1.0e-12,
            source_metric_whitener=source_metric_whitener,
            h_metric_whitener=h_metric_whitener,
            curvature_metric_whitener=curvature_metric_whitener,
            momentum_wires=tuple(momentum_wires),
            geometry_bundle=geometry_bundle,
            protocol_sha="0" * 64,
        )
        return self._resign_protocol(protocol)

    def test_exact_schema_freezes_every_pre_response_input(self) -> None:
        from rulespace_v3.scenario_response_protocol import (
            ApplicationScenarioResponseProtocolV2,
            issue_v3m0_scenario_response_protocol,
            verify_v3m0_scenario_response_protocol,
        )

        names = {item.name for item in fields(ApplicationScenarioResponseProtocolV2)}
        for required in (
            "formal_parent_v2_sha",
            "permit_v2_sha",
            "materialization_v2_sha",
            "operation_dag_sha",
            "compiled_contract_sha",
            "construction_trace_sha",
            "actual_factory_sha",
            "matched_ablated_factory_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "common_source_basis",
            "common_readout_basis",
            "source_selector",
            "readout_selector",
            "source_injection_isometry",
            "readout_coisometry",
            "selected_fejer_order",
            "response_reciprocal_indices",
            "source_bridge_reciprocal_indices",
            "readout_bridge_reciprocal_indices",
            "source_trial_vectors",
            "source_metric_whitener",
            "h_metric_whitener",
            "curvature_metric_whitener",
            "momentum_wires",
            "geometry_bundle",
            "protocol_sha",
        ):
            self.assertIn(required, names)
        self.assertEqual(
            tuple(inspect.signature(issue_v3m0_scenario_response_protocol).parameters),
            ("formal_parent_v2", "permit_v2", "materialization_v2"),
        )
        self.assertEqual(
            tuple(inspect.signature(verify_v3m0_scenario_response_protocol).parameters),
            ("value",),
        )

    def test_momentum_wire_literal_uses_the_current_c12_family_id(self) -> None:
        from typing import get_args, get_type_hints

        from rulespace_v3.scenario_response_protocol import (
            ScenarioResponseMomentumWireV2,
        )

        annotation = get_type_hints(ScenarioResponseMomentumWireV2)[
            "curvature_incidence_family_id"
        ]
        self.assertEqual(
            get_args(annotation),
            (
                "identity-incidence-v1",
                "synthetic-lattice-laplacian-incidence-v1",
            ),
        )

    def test_delayed_upstream_wiring_uses_exact_v2_public_consumers(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            VerifiedCalibrationApplicationPermitV2,
            require_calibration_application_permit_v2,
        )
        from rulespace_v3.application_materialization_v2 import (
            VerifiedV3M0ApplicationScenarioMaterializationV2,
            verify_v3m0_application_scenario_materialization_v2,
        )
        from rulespace_v3.scenario_response_protocol import (
            UPSTREAM_V2_WIRING_POINTS,
            _load_exact_v2_upstream,
        )

        self.assertEqual(
            UPSTREAM_V2_WIRING_POINTS,
            (
                "rulespace_v3.application_authority_v2."
                "VerifiedCalibrationApplicationPermitV2",
                "rulespace_v3.application_authority_v2."
                "require_calibration_application_permit_v2",
                "rulespace_v3.application_materialization_v2."
                "VerifiedV3M0ApplicationScenarioMaterializationV2",
                "rulespace_v3.application_materialization_v2."
                "verify_v3m0_application_scenario_materialization_v2",
            ),
        )
        self.assertEqual(
            _load_exact_v2_upstream(),
            (
                VerifiedCalibrationApplicationPermitV2,
                require_calibration_application_permit_v2,
                VerifiedV3M0ApplicationScenarioMaterializationV2,
                verify_v3m0_application_scenario_materialization_v2,
            ),
        )

    def test_raw_body_replays_basis_direction_and_self_hash(self) -> None:
        from rulespace_v3.scenario_response_protocol import (
            verify_application_scenario_response_protocol_v2_body,
        )

        protocol = self._protocol(laplacian=True, geometry=False)
        self.assertIs(
            verify_application_scenario_response_protocol_v2_body(protocol),
            protocol,
        )

    def test_curvature_whitener_dimension_matches_every_incidence_output(
        self,
    ) -> None:
        from rulespace_v3.factory import freeze_complex_tensor
        from rulespace_v3.scenario_response_protocol import (
            verify_application_scenario_response_protocol_v2_body,
        )

        protocol = self._protocol(laplacian=True, geometry=False)
        hostile = self._resign_protocol(
            replace(
                protocol,
                curvature_metric_whitener=freeze_complex_tensor(
                    np.eye(3, dtype=np.complex128)
                ),
            )
        )
        with self.assertRaisesRegex(ValueError, "curvature.*incidence output"):
            verify_application_scenario_response_protocol_v2_body(hostile)

    def test_exact_compiler_mechanically_binds_every_expected_input(
        self,
    ) -> None:
        import struct

        from rulespace_v3.factory import (
            freeze_complex_tensor,
            frozen_tensor_array,
        )
        from rulespace_v3.grids import (
            build_application_bridge_grid_manifest,
            build_response_grid_manifest,
        )
        from rulespace_v3.scenario_response_protocol import (
            ExpectedScenarioProtocolInputs,
            _make_exact_scenario_response_protocol_compiler,
        )
        from rulespace_v3.thresholds import BRIDGE_TOLERANCE

        protocol = self._protocol(laplacian=True, geometry=False)
        parent, permit, materialization = self._upstream_bodies(protocol)
        expected = self._expected_inputs(
            protocol,
            parent,
            permit,
            materialization,
        )
        self.assertIs(type(expected), ExpectedScenarioProtocolInputs)
        application = self._historical_application(protocol.control_case_id)
        response_grid = build_response_grid_manifest(application)
        bridge_grid = build_application_bridge_grid_manifest(application)
        self.assertEqual(expected.response_grid_sha, response_grid.response_grid_sha)
        self.assertEqual(
            expected.source_bridge_grid_sha,
            bridge_grid.bridge_grid_sha,
        )
        self.assertEqual(
            expected.readout_bridge_grid_sha,
            bridge_grid.bridge_grid_sha,
        )
        self.assertEqual(
            struct.pack("!d", expected.bridge_tolerance),
            struct.pack("!d", BRIDGE_TOLERANCE),
        )

        compiler = _make_exact_scenario_response_protocol_compiler(
            parent_body_type=type(parent),
            permit_body_type=type(permit),
            materialization_body_type=type(materialization),
            protocol_body_builder=lambda *_: protocol,
            expected_inputs_resolver=lambda *_: expected,
        )
        self.assertIs(compiler(parent, permit, materialization), protocol)

        polluted_expected = copy.deepcopy(expected)
        object.__setattr__(polluted_expected, "caller_override", "forged")
        polluted_compiler = _make_exact_scenario_response_protocol_compiler(
            parent_body_type=type(parent),
            permit_body_type=type(permit),
            materialization_body_type=type(materialization),
            protocol_body_builder=lambda *_: protocol,
            expected_inputs_resolver=lambda *_: polluted_expected,
        )
        with self.assertRaisesRegex(ValueError, "unknown or missing"):
            polluted_compiler(parent, permit, materialization)

        attacks = (
            ("response_grid_sha", "e" * 64),
            ("source_bridge_grid_sha", "f" * 64),
            ("readout_bridge_grid_sha", "1" * 64),
            (
                "bridge_tolerance",
                float(np.nextafter(BRIDGE_TOLERANCE, math.inf)),
            ),
            (
                "source_metric_whitener",
                freeze_complex_tensor(
                    2.0 * frozen_tensor_array(protocol.source_metric_whitener)
                ),
            ),
            (
                "h_metric_whitener",
                freeze_complex_tensor(
                    2.0 * frozen_tensor_array(protocol.h_metric_whitener)
                ),
            ),
            (
                "curvature_metric_whitener",
                freeze_complex_tensor(
                    2.0
                    * frozen_tensor_array(protocol.curvature_metric_whitener)
                ),
            ),
        )
        for field, attacked_value in attacks:
            with self.subTest(field=field):
                hostile = self._resign_protocol(
                    replace(protocol, **{field: attacked_value})
                )
                hostile_compiler = _make_exact_scenario_response_protocol_compiler(
                    parent_body_type=type(parent),
                    permit_body_type=type(permit),
                    materialization_body_type=type(materialization),
                    protocol_body_builder=lambda *_, value=hostile: value,
                    expected_inputs_resolver=lambda *_: expected,
                )
                with self.assertRaisesRegex(ValueError, field):
                    hostile_compiler(parent, permit, materialization)

    def test_metric_restriction_is_derived_not_temporary_identity(self) -> None:
        from rulespace_v3.factory import (
            freeze_complex_tensor,
            frozen_tensor_array,
        )
        from rulespace_v3.scenario_response_protocol import (
            _restrict_metric_whitener,
        )

        common = freeze_complex_tensor(
            np.diag(np.asarray((2.0, 3.0), dtype=np.complex128))
        )
        embedding = np.asarray(
            ((1.0 / math.sqrt(2.0),), (1.0 / math.sqrt(2.0),)),
            dtype=np.complex128,
        )
        restricted = frozen_tensor_array(
            _restrict_metric_whitener(
                common,
                embedding,
                field="test metric",
            )
        )
        common_values = frozen_tensor_array(common)
        expected_metric = (
            embedding.conj().T
            @ common_values.conj().T
            @ common_values
            @ embedding
        )
        self.assertTrue(
            np.allclose(
                restricted.conj().T @ restricted,
                expected_metric,
                rtol=0.0,
                atol=1.0e-15,
            )
        )
        self.assertFalse(np.array_equal(restricted, np.eye(1)))

    def test_readout_manifest_conjugation_cannot_be_resigned_away(self) -> None:
        from rulespace_v3.factory import basis_manifest_array, freeze_complex_tensor
        from rulespace_v3.scenario_response_protocol import (
            verify_application_scenario_response_protocol_v2_body,
        )

        protocol = self._protocol()
        selector = np.asarray(((1.0, 0.0),), dtype=np.complex128)
        hostile = replace(
            protocol,
            readout_coisometry=freeze_complex_tensor(
                selector @ basis_manifest_array(protocol.common_readout_basis)
            ),
        )
        hostile = self._resign_protocol(hostile)
        with self.assertRaisesRegex(ValueError, "readout_coisometry"):
            verify_application_scenario_response_protocol_v2_body(hostile)

    def test_resigned_scenario_and_geometry_splices_fail(self) -> None:
        from rulespace_v3.scenario_response_protocol import (
            verify_application_scenario_response_protocol_v2_body,
        )

        protocol = self._protocol()
        hostile_momentum = replace(
            protocol.momentum_wires[0],
            scenario_id="v3m0.hostile.scenario",
        )
        hostile_momentum = self._resign_momentum(hostile_momentum)
        hostile = self._resign_protocol(
            replace(
                protocol,
                momentum_wires=(hostile_momentum, *protocol.momentum_wires[1:]),
            )
        )
        with self.assertRaisesRegex(ValueError, "spliced"):
            verify_application_scenario_response_protocol_v2_body(hostile)

        hostile_geometry = replace(
            protocol.geometry_bundle,
            scenario_sha="f" * 64,
        )
        hostile_geometry = self._resign_geometry(hostile_geometry)
        hostile = self._resign_protocol(
            replace(protocol, geometry_bundle=hostile_geometry)
        )
        with self.assertRaisesRegex(ValueError, "geometry.*spliced"):
            verify_application_scenario_response_protocol_v2_body(hostile)

    def test_one_ulp_nu_attack_fails_even_after_recursive_resigning(self) -> None:
        from rulespace_v3.scenario_response_protocol import (
            verify_application_scenario_response_protocol_v2_body,
        )

        protocol = self._protocol(laplacian=True, geometry=False)
        momentum = protocol.momentum_wires[0]
        attacked_nu = float(np.nextafter(momentum.curvature_normalizer_value, math.inf))
        hostile_momentum = self._resign_momentum(
            replace(momentum, curvature_normalizer_value=attacked_nu)
        )
        hostile = self._resign_protocol(
            replace(
                protocol,
                momentum_wires=(hostile_momentum, *protocol.momentum_wires[1:]),
            )
        )
        with self.assertRaisesRegex(ValueError, "normalizer"):
            verify_application_scenario_response_protocol_v2_body(hostile)

    def test_full_c12_control_id_requires_momentum_local_laplacian(self) -> None:
        from rulespace_v3.scenario_response_protocol import (
            verify_application_scenario_response_protocol_v2_body,
        )

        protocol = self._resign_protocol(
            replace(
                self._protocol(geometry=False),
                control_case_id="C12_NU_INC_IR_NORMALIZATION",
            )
        )
        with self.assertRaisesRegex(ValueError, "C12.*Laplacian"):
            verify_application_scenario_response_protocol_v2_body(protocol)

    def test_private_exact_compiler_accepts_only_one_complete_upstream_lineage(
        self,
    ) -> None:
        from rulespace_v3.scenario_response_protocol import (
            _make_exact_scenario_response_protocol_compiler,
        )

        protocol = self._protocol(laplacian=True, geometry=False)
        parent, permit, materialization = self._upstream_bodies(protocol)
        compiler = _make_exact_scenario_response_protocol_compiler(
            parent_body_type=type(parent),
            permit_body_type=type(permit),
            materialization_body_type=type(materialization),
            protocol_body_builder=lambda *_: protocol,
            expected_inputs_resolver=lambda *_: self._expected_inputs(
                protocol, parent, permit, materialization
            ),
        )
        self.assertIs(compiler(parent, permit, materialization), protocol)

        hostile_materialization = copy.copy(materialization)
        hostile_materialization.permit_v2_sha = "f" * 64
        with self.assertRaisesRegex(ValueError, "permit"):
            compiler(parent, permit, hostile_materialization)

        hostile_protocol = self._resign_protocol(
            replace(protocol, scenario_id="v3m0.hostile.scenario")
        )
        hostile_compiler = _make_exact_scenario_response_protocol_compiler(
            parent_body_type=type(parent),
            permit_body_type=type(permit),
            materialization_body_type=type(materialization),
            protocol_body_builder=lambda *_: hostile_protocol,
            expected_inputs_resolver=lambda *_: self._expected_inputs(
                protocol, parent, permit, materialization
            ),
        )
        with self.assertRaisesRegex(ValueError, "scenario"):
            hostile_compiler(parent, permit, materialization)

        from rulespace_v3.factory import freeze_complex_tensor, frozen_tensor_array

        wire = protocol.momentum_wires[0]
        hostile_wire = self._resign_momentum(
            replace(
                wire,
                curvature_incidence_operator=freeze_complex_tensor(
                    2.0 * frozen_tensor_array(wire.curvature_incidence_operator)
                ),
                normalized_curvature_incidence_operator=freeze_complex_tensor(
                    2.0
                    * frozen_tensor_array(
                        wire.normalized_curvature_incidence_operator
                    )
                ),
            )
        )
        hostile_protocol = self._resign_protocol(
            replace(
                protocol,
                momentum_wires=(hostile_wire, *protocol.momentum_wires[1:]),
            )
        )
        hostile_compiler = _make_exact_scenario_response_protocol_compiler(
            parent_body_type=type(parent),
            permit_body_type=type(permit),
            materialization_body_type=type(materialization),
            protocol_body_builder=lambda *_: hostile_protocol,
            expected_inputs_resolver=lambda *_: self._expected_inputs(
                protocol, parent, permit, materialization
            ),
        )
        with self.assertRaisesRegex(ValueError, "momentum_wires"):
            hostile_compiler(parent, permit, materialization)

    def test_private_live_replayer_rejects_value_equal_fresh_capabilities(
        self,
    ) -> None:
        from rulespace_v3.scenario_response_protocol import (
            _make_exact_scenario_response_protocol_compiler,
            _make_live_scenario_response_protocol_replayer,
        )

        protocol = self._protocol(laplacian=True, geometry=False)
        parent_body, permit_body, materialization_body = self._upstream_bodies(
            protocol
        )

        class ParentCapability:
            pass

        class PermitCapability:
            pass

        class MaterializationCapability:
            pass

        parent = ParentCapability()
        permit = PermitCapability()
        materialization = MaterializationCapability()

        def identity_reverifier(expected, body, label):
            def require(value):
                if value is not expected:
                    raise ValueError(f"{label} identity is not live")
                return body

            return require

        compiler = _make_exact_scenario_response_protocol_compiler(
            parent_body_type=type(parent_body),
            permit_body_type=type(permit_body),
            materialization_body_type=type(materialization_body),
            protocol_body_builder=lambda *_: protocol,
            expected_inputs_resolver=lambda *_: self._expected_inputs(
                protocol, parent_body, permit_body, materialization_body
            ),
        )
        replay = _make_live_scenario_response_protocol_replayer(
            parent_capability_type=ParentCapability,
            permit_capability_type=PermitCapability,
            materialization_capability_type=MaterializationCapability,
            parent_reverifier=identity_reverifier(
                parent,
                parent_body,
                "Parent",
            ),
            permit_reverifier=identity_reverifier(
                permit,
                permit_body,
                "permit",
            ),
            materialization_reverifier=identity_reverifier(
                materialization,
                materialization_body,
                "materialization",
            ),
            upstream_relationship_verifier=lambda *_: None,
            exact_compiler=compiler,
        )
        self.assertIs(replay(parent, permit, materialization), protocol)
        with self.assertRaisesRegex(ValueError, "identity is not live"):
            replay(ParentCapability(), permit, materialization)
        with self.assertRaisesRegex(ValueError, "identity is not live"):
            replay(parent, PermitCapability(), materialization)
        with self.assertRaisesRegex(ValueError, "identity is not live"):
            replay(parent, permit, MaterializationCapability())

    def test_live_replayer_requires_the_same_cross_module_identity_chain(self) -> None:
        from rulespace_v3.scenario_response_protocol import (
            _make_exact_scenario_response_protocol_compiler,
            _make_live_scenario_response_protocol_replayer,
        )

        protocol = self._protocol(laplacian=True, geometry=False)
        parent_body, permit_body, materialization_body = self._upstream_bodies(
            protocol
        )

        class ParentCapability:
            pass

        class PermitCapability:
            pass

        class MaterializationCapability:
            pass

        parent_a, parent_b = ParentCapability(), ParentCapability()
        permit_a, permit_b = PermitCapability(), PermitCapability()
        materialization_a = MaterializationCapability()

        def accept_pair(first, second, body, label):
            def require(value):
                if value is not first and value is not second:
                    raise ValueError(f"{label} identity is not live")
                return body

            return require

        compiler = _make_exact_scenario_response_protocol_compiler(
            parent_body_type=type(parent_body),
            permit_body_type=type(permit_body),
            materialization_body_type=type(materialization_body),
            protocol_body_builder=lambda *_: protocol,
            expected_inputs_resolver=lambda *_: self._expected_inputs(
                protocol, parent_body, permit_body, materialization_body
            ),
        )

        allowed_chains = (
            (parent_a, permit_a, materialization_a),
        )

        def verify_relationship(parent, permit, materialization):
            if not any(
                parent is expected_parent
                and permit is expected_permit
                and materialization is expected_materialization
                for expected_parent, expected_permit, expected_materialization in (
                    allowed_chains
                )
            ):
                raise ValueError("cross-module live identity chain drifted")

        replay = _make_live_scenario_response_protocol_replayer(
            parent_capability_type=ParentCapability,
            permit_capability_type=PermitCapability,
            materialization_capability_type=MaterializationCapability,
            parent_reverifier=accept_pair(
                parent_a,
                parent_b,
                parent_body,
                "Parent",
            ),
            permit_reverifier=accept_pair(
                permit_a,
                permit_b,
                permit_body,
                "permit",
            ),
            materialization_reverifier=lambda value: (
                materialization_body
                if value is materialization_a
                else (_ for _ in ()).throw(
                    ValueError("materialization identity is not live")
                )
            ),
            upstream_relationship_verifier=verify_relationship,
            exact_compiler=compiler,
        )
        self.assertIs(
            replay(parent_a, permit_a, materialization_a),
            protocol,
        )
        with self.assertRaisesRegex(ValueError, "cross-module"):
            replay(parent_b, permit_b, materialization_a)

    def test_exact_compiler_freezes_its_lineage_validation_call_graph(self) -> None:
        import rulespace_v3.scenario_response_protocol as protocol_module
        from rulespace_v3.scenario_response_protocol import (
            _make_exact_scenario_response_protocol_compiler,
        )

        protocol = self._protocol(laplacian=True, geometry=False)
        parent, permit, materialization = self._upstream_bodies(protocol)
        compiler = _make_exact_scenario_response_protocol_compiler(
            parent_body_type=type(parent),
            permit_body_type=type(permit),
            materialization_body_type=type(materialization),
            protocol_body_builder=lambda *_: protocol,
            expected_inputs_resolver=lambda *_: self._expected_inputs(
                protocol, parent, permit, materialization
            ),
        )
        hostile_materialization = copy.copy(materialization)
        hostile_materialization.permit_v2_sha = "f" * 64

        with patch.object(
            protocol_module,
            "_verify_exact_protocol_upstream_lineage",
            lambda *_: None,
        ):
            with self.assertRaisesRegex(ValueError, "permit"):
                compiler(parent, permit, hostile_materialization)

        with patch.object(
            protocol_module,
            "_lineage_equal",
            lambda *_: None,
        ):
            with self.assertRaisesRegex(ValueError, "permit"):
                compiler(parent, permit, hostile_materialization)

    def test_unknown_caller_field_and_draft_state_are_rejected(self) -> None:
        from rulespace_v3.scenario_response_protocol import (
            verify_application_scenario_response_protocol_v2_body,
        )

        attacked = copy.deepcopy(self._protocol())
        object.__setattr__(attacked, "caller_threshold_override", 0.0)
        with self.assertRaisesRegex(ValueError, "unknown or missing"):
            verify_application_scenario_response_protocol_v2_body(attacked)

        with self.assertRaisesRegex(ValueError, "state"):
            replace(
                self._protocol(),
                protocol_state="DRAFT_PARENT_BOUND_PRE_RESPONSE",
            )

    def test_raw_candidate_v1_draft_and_forged_capabilities_never_issue(self) -> None:
        from rulespace_v3.application_authority_v2 import (
            VerifiedCalibrationApplicationPermitV2,
        )
        from rulespace_v3.application_materialization_v2 import (
            VerifiedV3M0ApplicationScenarioMaterializationV2,
        )
        from rulespace_v3.parent_authority import VerifiedParentFreezeV2
        from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
        from rulespace_v3.parent_candidate_v2 import ParentFreezeCandidateV2Manifest
        from rulespace_v3.parent_v2_contracts import ParentFreezeV2Manifest
        from rulespace_v3.scenario_response_protocol import (
            VerifiedApplicationScenarioResponseProtocolV2,
            issue_v3m0_scenario_response_protocol,
            verify_v3m0_scenario_response_protocol,
        )

        foreign_parents = (
            issue_v3m0_parent_freeze(),
            object.__new__(ParentFreezeCandidateV2Manifest),
            object.__new__(ParentFreezeV2Manifest),
            self._protocol(),
        )
        for foreign in foreign_parents:
            with self.subTest(foreign=type(foreign).__name__):
                with self.assertRaises((TypeError, ValueError)):
                    issue_v3m0_scenario_response_protocol(
                        foreign,
                        object(),
                        object(),
                    )

        forged = object.__new__(VerifiedApplicationScenarioResponseProtocolV2)
        with self.assertRaises(ValueError):
            verify_v3m0_scenario_response_protocol(forged)
        with self.assertRaisesRegex(ValueError, "live registry"):
            issue_v3m0_scenario_response_protocol(
                object.__new__(VerifiedParentFreezeV2),
                object.__new__(VerifiedCalibrationApplicationPermitV2),
                object.__new__(
                    VerifiedV3M0ApplicationScenarioMaterializationV2
                ),
            )

    def test_public_issuer_has_no_caller_injection_surface(self) -> None:
        from rulespace_v3.scenario_response_protocol import (
            issue_v3m0_scenario_response_protocol,
        )

        with self.assertRaises(TypeError):
            issue_v3m0_scenario_response_protocol(
                object(),
                object(),
                object(),
                curvature_normalizer=1.0,
            )

    def test_public_authority_freezes_complete_live_replay_graph(self) -> None:
        import rulespace_v3.scenario_response_protocol as protocol_module
        from rulespace_v3.scenario_response_protocol import (
            VerifiedApplicationScenarioResponseProtocolV2,
            issue_v3m0_scenario_response_protocol,
        )

        protocol = self._protocol(laplacian=True, geometry=False)
        with patch.object(
            protocol_module,
            "_make_exact_scenario_response_protocol_compiler",
            return_value=lambda *_: protocol,
        ), patch.object(
            protocol_module,
            "_make_live_scenario_response_protocol_replayer",
            return_value=lambda *_: protocol,
        ):
            with self.assertRaises((TypeError, ValueError, RuntimeError)):
                issue_v3m0_scenario_response_protocol(
                    object(),
                    object(),
                    object(),
                )

        forged = object.__new__(
            VerifiedApplicationScenarioResponseProtocolV2
        )
        with patch.object(
            protocol_module,
            "verify_v3m0_scenario_response_protocol",
            return_value=protocol,
        ):
            with self.assertRaises((TypeError, ValueError, AttributeError)):
                _ = forged.protocol


if __name__ == "__main__":
    unittest.main()
