"""Tests for the inert C12 per-k incidence construction preflight."""

from __future__ import annotations

from dataclasses import replace
import inspect
import json
import math
import unittest
from unittest.mock import patch

import numpy as np

from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor, frozen_tensor_array
from rulespace_v3.parent_freeze import (
    build_v3m0_parent_freeze_candidate,
    parent_freeze_candidate_manifest_payload,
)


class C12AnalyticIncidenceCertificateTests(unittest.TestCase):
    def _resign_point(self, point, **changes):
        from rulespace_v3.c12_incidence_preflight import (
            c12_incidence_point_wire_payload,
        )

        provisional = replace(point, **changes, point_sha="0" * 64)
        return replace(
            provisional,
            point_sha=canonical_sha(
                c12_incidence_point_wire_payload(provisional)
            ),
        )

    def _resign_certificate(self, certificate, **changes):
        from rulespace_v3.c12_analytic_incidence import (
            c12_analytic_incidence_certificate_payload,
        )

        provisional = replace(
            certificate,
            **changes,
            certificate_sha="0" * 64,
        )
        return replace(
            provisional,
            certificate_sha=canonical_sha(
                c12_analytic_incidence_certificate_payload(provisional)
            ),
        )

    def test_analytic_builder_binds_formula_ir_and_four_authority_refs(
        self,
    ) -> None:
        from rulespace_v3.c12_analytic_incidence import (
            build_c12_analytic_incidence_certificate,
            c12_analytic_incidence_certificate_payload,
            verify_c12_analytic_incidence_certificate,
        )
        from rulespace_v3.c12_incidence_preflight import _build_ir_certificate

        self.assertEqual(
            tuple(
                inspect.signature(
                    build_c12_analytic_incidence_certificate
                ).parameters
            ),
            (),
        )
        self.assertEqual(
            tuple(
                inspect.signature(
                    verify_c12_analytic_incidence_certificate
                ).parameters
            ),
            ("certificate",),
        )
        certificate = build_c12_analytic_incidence_certificate()
        self.assertIs(
            verify_c12_analytic_incidence_certificate(certificate),
            certificate,
        )
        self.assertEqual(
            certificate.incidence_family_id,
            "synthetic-lattice-laplacian-incidence-v1",
        )
        self.assertEqual(
            certificate.normalizer_formula_id,
            "nu-inc-4-sum-sin2-half-v1",
        )
        self.assertEqual(
            certificate.normalizer_derivation_id,
            "2-exp(+ik)-exp(-ik)-centered-second-difference-v1",
        )
        self.assertEqual(
            certificate.ir_limit_formula_id,
            "lim-k-to-zero-nu-inc-over-k-squared-equals-one-v1",
        )
        self.assertEqual(certificate.ir_limit_order, 2)
        self.assertEqual(certificate.ir_limit_value, 1.0)
        self.assertEqual(
            certificate.ir_conclusion,
            "POSITIVE_SECOND_ORDER_UNIT_CONTINUUM_LIMIT",
        )
        self.assertTrue(certificate.positivity_certified)
        self.assertEqual(
            (
                certificate.absolute_signal_threshold_authority_ref,
                certificate.raw_bridge_noise_evidence_ref,
                certificate.raw_noise_absolute_threshold_authority_ref,
                certificate.relative_gap_threshold_authority_ref,
            ),
            (
                "WindowThresholdSelection.curv_tau_sig",
                "SourceReadoutBridgeAudit.curv_operator_error_max",
                "rulespace_v3.thresholds.BRIDGE_TOLERANCE",
                "rulespace_v3.thresholds.RAW_GAP_MIN",
            ),
        )
        self.assertEqual(
            certificate.certificate_sha,
            "3541648edbb0a4490654b9ddc8d0b870df9133afd8912c204a57110e03a1c91c",
        )
        self.assertEqual(
            certificate.certificate_sha,
            canonical_sha(
                c12_analytic_incidence_certificate_payload(certificate)
            ),
        )
        first, second = certificate.point_wires
        self.assertEqual(first.reciprocal_index, (1,))
        self.assertEqual(first.nu_value, 2.0 - math.sqrt(2.0))
        self.assertEqual(second.reciprocal_index, (2,))
        self.assertEqual(second.nu_value, 2.0)

        legacy = _build_ir_certificate()
        self.assertEqual(legacy.incidence_family_id, certificate.incidence_family_id)
        self.assertEqual(
            legacy.normalizer_formula_id,
            certificate.normalizer_formula_id,
        )
        self.assertEqual(
            legacy.symbol_formula_id,
            certificate.normalizer_derivation_id,
        )
        self.assertEqual(legacy.point_wires, certificate.point_wires)
        self.assertEqual(
            legacy.certificate_sha,
            "1d456c262368268b3f0be12d0dc30af735b75c468a9a78886cb4d503de497309",
        )

        with self.assertRaises(TypeError):
            build_c12_analytic_incidence_certificate(
                certificate_sha="f" * 64
            )
        with self.assertRaises(TypeError):
            build_c12_analytic_incidence_certificate(
                absolute_signal_threshold=0.0
            )

    def test_analytic_builder_never_enters_finite_response_svd_or_structure(
        self,
    ) -> None:
        import rulespace_v3.c12_incidence_preflight as c12
        import rulespace_v3.c12_analytic_incidence as analytic

        poisoned_calls = []

        def poison(label):
            def poisoned(*_, **__):
                poisoned_calls.append(label)
                raise AssertionError(f"analytic-only builder called {label}")

            return poisoned

        with (
            patch.object(
                c12,
                "_finite_response_at_point",
                poison("finite response"),
            ),
            patch.object(
                c12,
                "_build_structure_audits",
                poison("structure audit"),
            ),
            patch.object(
                c12,
                "_build_point_audit",
                poison("point SVD audit"),
            ),
            patch.object(
                c12,
                "compute_fejer_filtered_response",
                poison("Fejer response"),
            ),
            patch.object(c12.np.linalg, "svd", poison("SVD")),
        ):
            certificate = analytic.build_c12_analytic_incidence_certificate()
            analytic.verify_c12_analytic_incidence_certificate(certificate)
        self.assertEqual(poisoned_calls, [])

    def test_analytic_verifier_rejects_ulp_family_formula_index_and_refs(
        self,
    ) -> None:
        from rulespace_v3.c12_analytic_incidence import (
            build_c12_analytic_incidence_certificate,
            verify_c12_analytic_incidence_certificate,
        )

        certificate = build_c12_analytic_incidence_certificate()
        first = certificate.point_wires[0]
        one_ulp = self._resign_point(
            first,
            nu_value=float(np.nextafter(first.nu_value, math.inf)),
        )
        wrong_index = self._resign_point(
            first,
            reciprocal_index=(3,),
            momentum=3.0 * math.pi / 4.0,
            root_of_unity_power=3,
        )
        point_attacks = (
            one_ulp,
            wrong_index,
            self._resign_point(
                first,
                normalizer_formula_id="wrong-normalizer-formula-v1",
            ),
        )
        for attacked_point in point_attacks:
            attacked = self._resign_certificate(
                certificate,
                point_wires=(
                    attacked_point,
                    *certificate.point_wires[1:],
                ),
            )
            with self.subTest(point=attacked_point):
                with self.assertRaises((TypeError, ValueError)):
                    verify_c12_analytic_incidence_certificate(attacked)

        certificate_attacks = (
            {"incidence_family_id": "wrong-family-v1"},
            {"normalizer_formula_id": "wrong-formula-v1"},
            {"normalizer_derivation_id": "wrong-derivation-v1"},
            {
                "absolute_signal_threshold_authority_ref": (
                    "caller.threshold"
                )
            },
            {"raw_bridge_noise_evidence_ref": "caller.noise"},
            {
                "raw_noise_absolute_threshold_authority_ref": (
                    "caller.absolute"
                )
            },
            {"relative_gap_threshold_authority_ref": "caller.gap"},
        )
        for changes in certificate_attacks:
            attacked = self._resign_certificate(certificate, **changes)
            with self.subTest(changes=changes):
                with self.assertRaises((TypeError, ValueError)):
                    verify_c12_analytic_incidence_certificate(attacked)

        with self.assertRaisesRegex(ValueError, "SHA"):
            verify_c12_analytic_incidence_certificate(
                replace(certificate, certificate_sha="f" * 64)
            )

    def test_analytic_public_api_captures_module_rebinding(self) -> None:
        import rulespace_v3.c12_analytic_incidence as c12

        builder = c12.build_c12_analytic_incidence_certificate
        verifier = c12.verify_c12_analytic_incidence_certificate
        poisoned_calls = []

        def poison(label):
            def poisoned(*_, **__):
                poisoned_calls.append(label)
                raise AssertionError(f"rebound {label} was called")

            return poisoned

        with (
            patch.object(
                c12,
                "_make_c12_analytic_incidence_certificate",
                poison("certificate maker"),
            ),
            patch.object(
                c12,
                "_verify_c12_analytic_incidence_certificate_body",
                poison("certificate verifier"),
            ),
            patch.object(
                c12,
                "_build_analytic_incidence_point",
                poison("incidence point builder"),
            ),
            patch.object(
                c12,
                "_build_analytic_incidence_point_body",
                poison("incidence point replay"),
            ),
        ):
            certificate = builder()
            self.assertIs(verifier(certificate), certificate)
        self.assertEqual(poisoned_calls, [])

    def test_analytic_public_api_closes_record_method_globals(self) -> None:
        import rulespace_v3.c12_analytic_incidence as c12

        certificate = c12.build_c12_analytic_incidence_certificate()
        poisoned_calls = []

        def poison(label):
            def poisoned(*_, **__):
                poisoned_calls.append(label)
                raise AssertionError(f"record method reached live {label}")

            return poisoned

        with (
            patch.object(c12, "type", poison("type"), create=True),
            patch.object(c12, "_text", poison("_text")),
            patch.object(c12, "getattr", poison("getattr"), create=True),
        ):
            rebuilt = c12.build_c12_analytic_incidence_certificate()
            self.assertIs(
                c12.verify_c12_analytic_incidence_certificate(certificate),
                certificate,
            )
            self.assertEqual(rebuilt, certificate)
        self.assertEqual(poisoned_calls, [])

    def test_analytic_positivity_is_only_strict_away_from_zero(self) -> None:
        from rulespace_v3.c12_analytic_incidence import (
            C12_POSITIVITY_DOMAIN_ID,
            build_c12_analytic_incidence_certificate,
            verify_c12_analytic_incidence_certificate,
        )

        certificate = build_c12_analytic_incidence_certificate()
        self.assertEqual(
            C12_POSITIVITY_DOMAIN_ID,
            "one-dimensional-minus-pi-open-pi-closed-excluding-zero-v1",
        )
        self.assertEqual(
            certificate.positivity_domain_id,
            C12_POSITIVITY_DOMAIN_ID,
        )
        self.assertEqual(4.0 * math.sin(0.0 / 2.0) ** 2, 0.0)
        for point in certificate.point_wires:
            self.assertNotEqual(point.momentum, 0.0)
            self.assertGreater(point.nu_value, 0.0)

        attacked = self._resign_certificate(
            certificate,
            positivity_domain_id=(
                "one-dimensional-minus-pi-open-pi-closed-including-zero-v1"
            ),
        )
        with self.assertRaisesRegex(ValueError, "exact replay"):
            verify_c12_analytic_incidence_certificate(attacked)


class C12IncidencePreflightTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        from rulespace_v3.c12_incidence_preflight import (
            build_c12_incidence_preflight,
        )

        cls.candidate = build_v3m0_parent_freeze_candidate()
        cls.preflight = build_c12_incidence_preflight(cls.candidate)

    def test_builds_from_the_unique_verified_parent_candidate(self) -> None:
        from rulespace_v3.c12_incidence_preflight import (
            C12_SCENARIO_ID,
            verify_c12_incidence_preflight,
        )

        preflight = self.preflight
        self.assertEqual(preflight.scenario_id, C12_SCENARIO_ID)
        self.assertEqual(preflight.candidate_sha, self.candidate.candidate_sha)
        self.assertEqual(
            preflight.integration_state,
            "PREFLIGHT_ONLY_NO_BLOCK_NO_AUTHORITY",
        )
        self.assertIs(
            verify_c12_incidence_preflight(self.candidate, preflight),
            preflight,
        )

    def test_recipe_is_a_distinct_rank_two_local_four_channel_carrier(self) -> None:
        from rulespace_v3.c12_incidence_preflight import (
            c12_application_recipe_symbol,
        )

        recipe = self.preflight.recipe
        candidate_scenario = next(
            scenario
            for application in self.candidate.application_candidates
            if application.control_case_id == "C12_NU_INC_IR_NORMALIZATION"
            for scenario in application.scenario_candidates
        )
        self.assertEqual(
            recipe.construction_rule_id,
            "c12-rank-two-local-incidence-carrier-v1",
        )
        self.assertEqual(
            recipe.based_on_candidate_selector_sha,
            candidate_scenario.selector_spec.selector_sha,
        )
        self.assertEqual(recipe.candidate_expected_shell_rank, 1)
        self.assertEqual(recipe.proposed_expected_shell_rank, 2)
        self.assertEqual(
            recipe.selector_rank_refreeze_disposition,
            "REQUIRES_PARENT_SELECTOR_AND_RANK_REFREEZE",
        )
        self.assertEqual(
            recipe.readout_refreeze_disposition,
            "UNCHANGED_CURRENT_IDENTITY4",
        )
        self.assertEqual(
            recipe.candidate_selector_spec,
            candidate_scenario.selector_spec,
        )
        self.assertNotEqual(
            recipe.proposed_selector_spec.selector_sha,
            recipe.candidate_selector_spec.selector_sha,
        )
        self.assertEqual(recipe.channel_order, ("q0", "p0", "q1", "p1"))
        self.assertEqual(recipe.primitive_support_radius, 1)
        self.assertTrue(recipe.actual_steps)
        self.assertEqual(
            recipe.matched_ablated_steps,
            tuple(step for step in recipe.actual_steps if not step.target_conditioned),
        )
        self.assertTrue(any(step.target_conditioned for step in recipe.actual_steps))
        self.assertTrue(all(abs(step.offset[0]) <= 1 for step in recipe.actual_steps))
        self.assertFalse(recipe.uses_global_fft_projection)
        self.assertFalse(recipe.uses_per_k_time_step_projector)
        self.assertEqual(
            recipe.incidence_application_stage,
            "POST_RESPONSE_READOUT_ONLY",
        )
        for branch in ("actual", "matched_ablated"):
            for momentum in (math.pi / 4.0, math.pi / 2.0):
                matrix = c12_application_recipe_symbol(recipe, momentum, branch)
                self.assertEqual(matrix.shape, (4, 4))

    def test_source_is_first_two_common_semantic_columns_and_readout_is_i4(
        self,
    ) -> None:
        from rulespace_v3.geometry_application_recipes import (
            _common_semantic_basis,
        )

        recipe = self.preflight.recipe
        root_two = math.sqrt(2.0)
        half_root_two = 1.0 / (2.0 * root_two)
        closed_semantic_frame = np.asarray(
            (
                (1.0 / root_two, 0.0, 1.0 / root_two, 0.0),
                (
                    -1.0j * half_root_two,
                    -0.5 + 1.0j * half_root_two,
                    1.0j * half_root_two,
                    0.5 - 1.0j * half_root_two,
                ),
                (0.0, 1.0 / root_two, 0.0, 1.0 / root_two),
                (
                    0.5 + 1.0j * half_root_two,
                    1.0j * half_root_two,
                    -0.5 - 1.0j * half_root_two,
                    -1.0j * half_root_two,
                ),
            ),
            dtype=np.complex128,
        )
        expected = closed_semantic_frame[:, :2]
        candidate = recipe.candidate_selector_spec
        proposed = recipe.proposed_selector_spec
        self.assertEqual(frozen_tensor_array(candidate.source_injection).shape, (4, 4))
        self.assertEqual(frozen_tensor_array(proposed.source_injection).shape, (4, 2))
        self.assertEqual(
            np.linalg.matrix_rank(frozen_tensor_array(candidate.source_injection)),
            4,
        )
        self.assertEqual(
            np.linalg.matrix_rank(frozen_tensor_array(proposed.source_injection)),
            2,
        )
        np.testing.assert_array_equal(
            frozen_tensor_array(proposed.source_injection),
            expected,
        )
        self.assertEqual(
            recipe.semantic_frame_derivation_id,
            "analytic-common-geometry-semantic-frame-v1",
        )
        self.assertEqual(
            proposed.source_selector_derivation_id,
            "analytic-common-geometry-semantic-frame-first-two-columns-v1",
        )
        projector_frame = _common_semantic_basis(recipe.matched_ablated_steps)[:, :2]
        expected_subspace_residual = float(
            np.linalg.norm(
                projector_frame @ projector_frame.conj().T
                - expected @ expected.conj().T,
                ord=2,
            )
        )
        self.assertEqual(
            recipe.projector_frame_subspace_residual,
            expected_subspace_residual,
        )
        self.assertLessEqual(recipe.projector_frame_subspace_residual, 1.0e-12)
        np.testing.assert_array_equal(
            frozen_tensor_array(candidate.readout_coisometry),
            np.eye(4, dtype=np.complex128),
        )
        np.testing.assert_array_equal(
            frozen_tensor_array(proposed.readout_coisometry),
            np.eye(4, dtype=np.complex128),
        )
        source_selector = frozen_tensor_array(proposed.source_selector)
        candidate_source = frozen_tensor_array(candidate.source_injection)
        np.testing.assert_array_equal(
            candidate_source @ source_selector,
            frozen_tensor_array(proposed.source_injection),
        )

    def test_centered_stencil_and_cyclotomic_per_k_wires_are_exact(self) -> None:
        certificate = self.preflight.ir_certificate
        self.assertEqual(certificate.stencil_offsets, ((-1,), (0,), (1,)))
        self.assertEqual(certificate.stencil_coefficients, (-1, 2, -1))
        self.assertEqual(certificate.ir_limit_value, 1.0)
        self.assertEqual(certificate.ir_limit_order, 2)
        self.assertEqual(
            tuple(point.reciprocal_index for point in certificate.point_wires),
            ((1,), (2,)),
        )
        first, second = certificate.point_wires
        self.assertEqual(first.exact_nu_expression, "2 - sqrt(2)")
        self.assertEqual(first.nu_minimal_polynomial_coefficients, (1, -4, 2))
        self.assertEqual(second.exact_nu_expression, "2")
        self.assertEqual(second.nu_minimal_polynomial_coefficients, (1, -2))
        self.assertEqual(first.nu_value, 2.0 - math.sqrt(2.0))
        self.assertEqual(second.nu_value, 2.0)
        for point in certificate.point_wires:
            self.assertGreater(point.momentum, 0.0)
            self.assertLessEqual(point.momentum, math.pi)
            self.assertGreater(point.nu_value, 0.0)
            np.testing.assert_allclose(
                frozen_tensor_array(point.incidence_operator),
                point.nu_value * np.eye(4, dtype=np.complex128),
                rtol=0.0,
                atol=0.0,
            )
            np.testing.assert_allclose(
                frozen_tensor_array(point.normalized_incidence_operator),
                np.eye(4, dtype=np.complex128),
                rtol=0.0,
                atol=2.0e-16,
            )
            self.assertLessEqual(point.stencil_symbol_residual, 2.0e-15)

    def test_all_T_branch_k_audits_have_rank_two_and_finite_margins(self) -> None:
        from rulespace_v3.c12_incidence_preflight import C12_FEJER_ORDERS

        audits = self.preflight.point_audits
        self.assertEqual(len(audits), len(C12_FEJER_ORDERS) * 2 * 2)
        self.assertEqual(
            {
                (audit.selected_fejer_order, audit.branch, audit.reciprocal_index)
                for audit in audits
            },
            {
                (order, branch, reciprocal_index)
                for order in C12_FEJER_ORDERS
                for branch in ("actual", "matched_ablated")
                for reciprocal_index in ((1,), (2,))
            },
        )
        for audit in audits:
            with self.subTest(
                order=audit.selected_fejer_order,
                branch=audit.branch,
                k=audit.reciprocal_index,
            ):
                self.assertEqual(audit.endpoint_shell_rank, 2)
                self.assertGreater(audit.endpoint_participation, 0.25)
                self.assertEqual(audit.raw_rank, 2)
                self.assertEqual(audit.normalized_rank, 2)
                self.assertEqual(len(audit.raw_singular_values), 2)
                self.assertEqual(len(audit.normalized_singular_values), 2)
                self.assertIsNone(audit.raw_inactive_max)
                self.assertIsNone(audit.normalized_inactive_max)
                self.assertTrue(math.isfinite(audit.absolute_signal_margin))
                self.assertTrue(math.isfinite(audit.raw_bridge_noise_margin))
                self.assertTrue(math.isfinite(audit.relative_gap))
                self.assertTrue(math.isfinite(audit.relative_gap_margin))
                self.assertGreater(audit.absolute_signal_margin, 0.0)
                self.assertGreater(audit.raw_bridge_noise_margin, 0.0)
                self.assertGreater(audit.relative_gap_margin, 0.0)
                self.assertLessEqual(audit.raw_bridge_noise, 2.0e-12)
                raw = frozen_tensor_array(audit.raw_response)
                normalized = frozen_tensor_array(audit.normalized_response)
                self.assertEqual(raw.shape, (4, 2))
                self.assertEqual(normalized.shape, (4, 2))
                np.testing.assert_allclose(
                    raw / audit.nu_value,
                    normalized,
                    rtol=0.0,
                    atol=2.0e-15,
                )
                self.assertEqual(
                    audit.absolute_signal_margin,
                    audit.normalized_active_min
                    - self.preflight.absolute_signal_threshold,
                )
                self.assertEqual(
                    audit.raw_bridge_noise_margin,
                    self.preflight.raw_noise_absolute_threshold
                    - audit.raw_bridge_noise,
                )
                numerical_floor = float(
                    np.finfo(np.float64).eps
                    * max(1.0, audit.raw_singular_values[0])
                    * 64.0
                )
                expected_gap = audit.raw_active_min / max(
                    audit.raw_bridge_noise,
                    numerical_floor,
                )
                self.assertEqual(audit.relative_gap, expected_gap)
                self.assertEqual(
                    audit.relative_gap_margin,
                    expected_gap - self.preflight.relative_gap_threshold,
                )

    def test_l8_l16_bridge_and_fp64_structure_are_green(self) -> None:
        audits = self.preflight.structure_audits
        self.assertEqual(
            {(audit.branch, audit.lattice_size) for audit in audits},
            {
                (branch, lattice_size)
                for branch in ("actual", "matched_ablated")
                for lattice_size in (8, 16)
            },
        )
        support_by_branch = {}
        for audit in audits:
            self.assertLessEqual(audit.max_bridge_error, 2.0e-12)
            self.assertLessEqual(audit.max_unitary_error, 1.0e-12)
            self.assertLessEqual(audit.max_symplectic_error, 1.0e-12)
            self.assertLessEqual(audit.max_reality_error, 1.0e-12)
            support_by_branch.setdefault(audit.branch, set()).add(
                (audit.primitive_support_offsets, audit.composite_support_radius)
            )
        self.assertTrue(all(len(values) == 1 for values in support_by_branch.values()))

    def test_incidence_is_absent_from_every_time_step_payload(self) -> None:
        from rulespace_v3.application_recipes import (
            application_local_shear_step_payload,
        )

        for step in self.preflight.recipe.actual_steps:
            payload = application_local_shear_step_payload(step)
            serialized = json.dumps(payload, sort_keys=True).lower()
            for forbidden in ("incidence", "normalizer", "fft", "projector"):
                self.assertNotIn(forbidden, serialized)

    def test_legacy_identity4_rank1_contract_is_saved_as_a_no_go(self) -> None:
        no_go = self.preflight.legacy_no_go_audit
        self.assertEqual(no_go.legacy_source_id, "identity4")
        self.assertEqual(no_go.legacy_declared_shell_rank, 1)
        self.assertEqual(no_go.observed_rank, 4)
        self.assertGreater(no_go.off_band_active_min, no_go.absolute_signal_threshold)
        self.assertEqual(no_go.conclusion, "REJECT_IDENTITY4_AND_RANK1")

    def test_resigned_recipe_point_audit_and_top_level_splices_are_red(self) -> None:
        from rulespace_v3.c12_incidence_preflight import (
            c12_application_recipe_payload,
            c12_branch_point_audit_payload,
            c12_incidence_preflight_payload,
            verify_c12_incidence_preflight,
        )

        recipe = self.preflight.recipe
        from rulespace_v3.parent_freeze import scenario_basis_selector_spec_payload

        proposed0 = replace(
            recipe.proposed_selector_spec,
            source_injection=freeze_complex_tensor(np.eye(4, dtype=np.complex128)),
            selector_sha="0" * 64,
        )
        resigned_proposed = replace(
            proposed0,
            selector_sha=canonical_sha(scenario_basis_selector_spec_payload(proposed0)),
        )
        provisional_recipe = replace(
            recipe,
            proposed_selector_spec=resigned_proposed,
            recipe_sha="0" * 64,
        )
        resigned_recipe = replace(
            provisional_recipe,
            recipe_sha=canonical_sha(
                c12_application_recipe_payload(provisional_recipe)
            ),
        )
        provisional_preflight = replace(
            self.preflight,
            recipe=resigned_recipe,
            preflight_sha="0" * 64,
        )
        resigned_preflight = replace(
            provisional_preflight,
            preflight_sha=canonical_sha(
                c12_incidence_preflight_payload(provisional_preflight)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_c12_incidence_preflight(self.candidate, resigned_preflight)

        for changes in (
            {"candidate_expected_shell_rank": 2},
            {"proposed_expected_shell_rank": 1},
            {"selector_rank_refreeze_disposition": "CURRENT_PARENT_APPROVED"},
            {"readout_refreeze_disposition": "REQUIRES_PARENT_REFREEZE"},
        ):
            with self.subTest(recipe_changes=changes):
                with self.assertRaises((TypeError, ValueError)):
                    replace(recipe, **changes).__post_init__()

        first = self.preflight.point_audits[0]
        provisional_audit = replace(
            first,
            branch="unknown",  # type: ignore[arg-type]
            audit_sha="0" * 64,
        )
        resigned_audit = replace(
            provisional_audit,
            audit_sha=canonical_sha(c12_branch_point_audit_payload(provisional_audit)),
        )
        provisional_preflight = replace(
            self.preflight,
            point_audits=(resigned_audit, *self.preflight.point_audits[1:]),
            preflight_sha="0" * 64,
        )
        resigned_preflight = replace(
            provisional_preflight,
            preflight_sha=canonical_sha(
                c12_incidence_preflight_payload(provisional_preflight)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_c12_incidence_preflight(self.candidate, resigned_preflight)

    def test_k0_bz_nu_formula_stencil_T_and_projector_splices_are_red(self) -> None:
        from rulespace_v3.c12_incidence_preflight import (
            c12_incidence_point_wire_payload,
            c12_incidence_preflight_payload,
            c12_ir_limit_certificate_payload,
            verify_c12_incidence_preflight,
        )

        def resign_top(**changes: object):
            provisional = replace(
                self.preflight,
                **changes,
                preflight_sha="0" * 64,
            )
            return replace(
                provisional,
                preflight_sha=canonical_sha(
                    c12_incidence_preflight_payload(provisional)
                ),
            )

        first = self.preflight.ir_certificate.point_wires[0]
        for changes in (
            {"momentum": 0.0},
            {"momentum": math.pi + 0.1},
            {"nu_value": first.nu_value + 0.01},
            {"normalizer_formula_id": "wrong-formula-v1"},
        ):
            provisional = replace(first, **changes, point_sha="0" * 64)
            point = replace(
                provisional,
                point_sha=canonical_sha(c12_incidence_point_wire_payload(provisional)),
            )
            certificate0 = replace(
                self.preflight.ir_certificate,
                point_wires=(point, self.preflight.ir_certificate.point_wires[1]),
                certificate_sha="0" * 64,
            )
            certificate = replace(
                certificate0,
                certificate_sha=canonical_sha(
                    c12_ir_limit_certificate_payload(certificate0)
                ),
            )
            with self.subTest(point_changes=changes):
                with self.assertRaises((TypeError, ValueError)):
                    verify_c12_incidence_preflight(
                        self.candidate,
                        resign_top(ir_certificate=certificate),
                    )

        certificate0 = replace(
            self.preflight.ir_certificate,
            stencil_coefficients=(1, -2, 1),
            certificate_sha="0" * 64,
        )
        certificate = replace(
            certificate0,
            certificate_sha=canonical_sha(
                c12_ir_limit_certificate_payload(certificate0)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_c12_incidence_preflight(
                self.candidate,
                resign_top(ir_certificate=certificate),
            )

        audit = self.preflight.point_audits[0]
        with self.assertRaises((TypeError, ValueError)):
            replace(audit, selected_fejer_order=257).__post_init__()
        with self.assertRaises((TypeError, ValueError)):
            replace(
                self.preflight.recipe,
                uses_global_fft_projection=True,
            ).__post_init__()
        with self.assertRaises((TypeError, ValueError)):
            replace(
                self.preflight.recipe,
                uses_per_k_time_step_projector=True,
            ).__post_init__()

    def test_resigned_parent_candidate_and_unknown_fields_are_red(self) -> None:
        from rulespace_v3.c12_incidence_preflight import (
            build_c12_incidence_preflight,
            verify_c12_incidence_preflight,
        )

        provisional = replace(
            self.candidate,
            proposed_parent_freeze_schema_version="v3m0.parent-freeze.v999",
            candidate_sha="0" * 64,
        )
        resigned = replace(
            provisional,
            candidate_sha=canonical_sha(
                parent_freeze_candidate_manifest_payload(provisional)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            build_c12_incidence_preflight(resigned)

        unknown = replace(self.preflight)
        object.__setattr__(unknown, "unknown_field", "hostile")
        with self.assertRaises((TypeError, ValueError)):
            verify_c12_incidence_preflight(self.candidate, unknown)


if __name__ == "__main__":
    unittest.main()
