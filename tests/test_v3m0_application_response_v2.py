"""Exact and opaque application-response v2 authority tests."""

from __future__ import annotations

from dataclasses import replace
import inspect
import unittest

import numpy as np


SHA0 = "0" * 64
SHA1 = "1" * 64
SHA2 = "2" * 64
SHA3 = "3" * 64
SHA4 = "4" * 64
SHA5 = "5" * 64
SHA6 = "6" * 64
SHA7 = "7" * 64
SHA8 = "8" * 64
SHA9 = "9" * 64
SHAA = "a" * 64
SHAB = "b" * 64
SHAC = "c" * 64
SHAD = "d" * 64
SHAE = "e" * 64
SHAF = "f" * 64


class _Bodies:
    def _resign_run_spec(self, value):
        from rulespace_v3.application_response import (
            application_response_run_spec_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, run_spec_sha=SHA0)
        return replace(
            provisional,
            run_spec_sha=canonical_sha(
                application_response_run_spec_v2_payload(provisional)
            ),
        )

    def _run_spec(self):
        from rulespace_v3.application_response import (
            APPLICATION_RESPONSE_RUN_SPEC_V2_SCHEMA_VERSION,
            ApplicationResponseRunSpecV2,
        )
        from rulespace_v3.factory import freeze_complex_tensor

        return self._resign_run_spec(
            ApplicationResponseRunSpecV2(
                run_spec_schema_version=(
                    APPLICATION_RESPONSE_RUN_SPEC_V2_SCHEMA_VERSION
                ),
                formal_parent_v2_sha=SHA1,
                permit_v2_sha=SHA2,
                materialization_v2_sha=SHA3,
                scenario_response_protocol_v2_sha=SHA4,
                control_case_id="C17",
                scenario_id="C17.quotient-gauge",
                scenario_sha=SHA5,
                selected_fejer_order=256,
                state_schema_id="v3m0.test.two-channel.v2",
                channel_order=("q", "p"),
                spatial_shape=(8, 8),
                response_reciprocal_indices=((0, 0), (1, 0)),
                source_readout_bridge_reciprocal_indices=((0, 0), (1, 0)),
                source_readout_bridge_steps=(1, 2, 4),
                reference_reciprocal_index=(0, 0),
                source_injection_isometry=freeze_complex_tensor(
                    np.eye(2, dtype=np.complex128)
                ),
                readout_coisometry=freeze_complex_tensor(
                    np.eye(2, dtype=np.complex128)
                ),
                run_spec_sha=SHA0,
            )
        )

    def _resign_authority(self, value):
        from rulespace_v3.application_response import (
            application_response_authority_binding_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, authority_binding_sha=SHA0)
        return replace(
            provisional,
            authority_binding_sha=canonical_sha(
                application_response_authority_binding_v2_payload(provisional)
            ),
        )

    def _authority(self, run_spec=None):
        from rulespace_v3.application_response import (
            APPLICATION_RESPONSE_AUTHORITY_BINDING_V2_SCHEMA_VERSION,
            ApplicationResponseAuthorityBindingV2,
        )

        run_spec = self._run_spec() if run_spec is None else run_spec
        return self._resign_authority(
            ApplicationResponseAuthorityBindingV2(
                authority_schema_version=(
                    APPLICATION_RESPONSE_AUTHORITY_BINDING_V2_SCHEMA_VERSION
                ),
                authority_state="CURRENT_PARENT_V2_RESPONSE_CHAIN_BOUND",
                formal_parent_v2_sha=run_spec.formal_parent_v2_sha,
                permit_v2_sha=run_spec.permit_v2_sha,
                materialization_v2_sha=run_spec.materialization_v2_sha,
                scenario_response_protocol_v2_sha=(
                    run_spec.scenario_response_protocol_v2_sha
                ),
                run_spec_sha=run_spec.run_spec_sha,
                control_case_id=run_spec.control_case_id,
                scenario_id=run_spec.scenario_id,
                scenario_sha=run_spec.scenario_sha,
                actual_factory_sha=SHA6,
                matched_ablated_factory_sha=SHA7,
                actual_prestructure_authority_sha=SHA8,
                matched_ablated_prestructure_authority_sha=SHA9,
                actual_transition_sha=SHAA,
                matched_ablated_transition_sha=SHAB,
                actual_dynamics_certificate_sha=SHAC,
                matched_ablated_dynamics_certificate_sha=SHAD,
                certificate_backed_qualification_sha=SHAE,
                authority_binding_sha=SHA0,
            )
        )

    def _resign_reference(self, value):
        from rulespace_v3.application_response import (
            application_endpoint_reference_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, endpoint_reference_sha=SHA0)
        return replace(
            provisional,
            endpoint_reference_sha=canonical_sha(
                application_endpoint_reference_v2_payload(provisional)
            ),
        )

    def _reference(self, run_spec=None, authority=None):
        from rulespace_v3.application_response import (
            APPLICATION_ENDPOINT_REFERENCE_V2_SCHEMA_VERSION,
            ApplicationEndpointReferenceV2,
        )
        from rulespace_v3.factory import freeze_complex_tensor

        run_spec = self._run_spec() if run_spec is None else run_spec
        authority = self._authority(run_spec) if authority is None else authority
        return self._resign_reference(
            ApplicationEndpointReferenceV2(
                endpoint_reference_schema_version=(
                    APPLICATION_ENDPOINT_REFERENCE_V2_SCHEMA_VERSION
                ),
                branch="actual",
                authority_binding=authority,
                run_spec=run_spec,
                actual_transition_sha=authority.actual_transition_sha,
                actual_dynamics_certificate_sha=(
                    authority.actual_dynamics_certificate_sha
                ),
                reference_reciprocal_index=(0, 0),
                preregistered_phase_band=(0.1, 0.5),
                reference_phase=0.25,
                expected_shell_rank=2,
                rank=2,
                participation=1.0,
                runner_up_overlap=None,
                hermitian_residual=0.0,
                idempotent_residual=0.0,
                metric_invariance_residual=0.0,
                eigenphase_residual=0.0,
                projector=freeze_complex_tensor(
                    np.eye(2, dtype=np.complex128)
                ),
                endpoint_reference_sha=SHA0,
            )
        )

    def _resign_shell(self, value):
        from rulespace_v3.application_response import (
            application_endpoint_shell_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, endpoint_shell_sha=SHA0)
        return replace(
            provisional,
            endpoint_shell_sha=canonical_sha(
                application_endpoint_shell_v2_payload(provisional)
            ),
        )

    def _shell(self, run_spec=None, authority=None, reference=None):
        from rulespace_v3.application_response import (
            APPLICATION_ENDPOINT_SHELL_V2_SCHEMA_VERSION,
            ApplicationEndpointShellV2,
        )
        from rulespace_v3.factory import freeze_complex_tensor

        run_spec = self._run_spec() if run_spec is None else run_spec
        authority = self._authority(run_spec) if authority is None else authority
        reference = (
            self._reference(run_spec, authority)
            if reference is None
            else reference
        )
        return self._resign_shell(
            ApplicationEndpointShellV2(
                endpoint_shell_schema_version=(
                    APPLICATION_ENDPOINT_SHELL_V2_SCHEMA_VERSION
                ),
                branch="actual",
                authority_binding=authority,
                run_spec=run_spec,
                endpoint_reference=reference,
                actual_transition_sha=authority.actual_transition_sha,
                actual_dynamics_certificate_sha=(
                    authority.actual_dynamics_certificate_sha
                ),
                shell_phases=(0.25, 0.25),
                shell_projectors=freeze_complex_tensor(
                    np.stack(
                        (
                            np.eye(2, dtype=np.complex128),
                            np.eye(2, dtype=np.complex128),
                        )
                    )
                ),
                point_participations=(1.0, 1.0),
                hermitian_residual_max=0.0,
                idempotent_residual_max=0.0,
                metric_invariance_residual_max=0.0,
                eigenphase_residual_max=0.0,
                endpoint_shell_sha=SHA0,
            )
        )

    def _resign_branch_response(self, value):
        from rulespace_v3.application_response import (
            application_branch_source_readout_response_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, branch_response_sha=SHA0)
        return replace(
            provisional,
            branch_response_sha=canonical_sha(
                application_branch_source_readout_response_v2_payload(
                    provisional
                )
            ),
        )

    def _branch_response(
        self,
        branch,
        *,
        run_spec=None,
        authority=None,
        shell=None,
    ):
        from rulespace_v3.application_response import (
            APPLICATION_BRANCH_SOURCE_READOUT_RESPONSE_V2_SCHEMA_VERSION,
            ApplicationBranchSourceReadoutResponseV2,
        )
        from rulespace_v3.factory import freeze_complex_tensor

        run_spec = self._run_spec() if run_spec is None else run_spec
        authority = self._authority(run_spec) if authority is None else authority
        shell = self._shell(run_spec, authority) if shell is None else shell
        actual = branch == "actual"
        return self._resign_branch_response(
            ApplicationBranchSourceReadoutResponseV2(
                branch_response_schema_version=(
                    APPLICATION_BRANCH_SOURCE_READOUT_RESPONSE_V2_SCHEMA_VERSION
                ),
                branch=branch,
                authority_binding=authority,
                run_spec=run_spec,
                actual_endpoint_shell=shell,
                factory_sha=(
                    authority.actual_factory_sha
                    if actual
                    else authority.matched_ablated_factory_sha
                ),
                prestructure_authority_sha=(
                    authority.actual_prestructure_authority_sha
                    if actual
                    else authority.matched_ablated_prestructure_authority_sha
                ),
                transition_sha=(
                    authority.actual_transition_sha
                    if actual
                    else authority.matched_ablated_transition_sha
                ),
                dynamics_certificate_sha=(
                    authority.actual_dynamics_certificate_sha
                    if actual
                    else authority.matched_ablated_dynamics_certificate_sha
                ),
                source_readout_bridge_sha=(SHAF if actual else SHA5),
                response_values=freeze_complex_tensor(
                    np.stack(
                        (
                            np.eye(2, dtype=np.complex128),
                            np.eye(2, dtype=np.complex128),
                        )
                    )
                ),
                branch_response_sha=SHA0,
            )
        )

    def _resign_pair(self, value):
        from rulespace_v3.application_response import (
            application_paired_response_outcome_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        provisional = replace(value, atomic_pair_sha=SHA0)
        return replace(
            provisional,
            atomic_pair_sha=canonical_sha(
                application_paired_response_outcome_v2_payload(provisional)
            ),
        )

    def _pair(self):
        from rulespace_v3.application_response import (
            APPLICATION_PAIRED_RESPONSE_OUTCOME_V2_SCHEMA_VERSION,
            ApplicationPairedResponseOutcomeV2,
        )

        run_spec = self._run_spec()
        authority = self._authority(run_spec)
        shell = self._shell(run_spec, authority)
        actual = self._branch_response(
            "actual",
            run_spec=run_spec,
            authority=authority,
            shell=shell,
        )
        matched = self._branch_response(
            "matched_ablated",
            run_spec=run_spec,
            authority=authority,
            shell=shell,
        )
        return self._resign_pair(
            ApplicationPairedResponseOutcomeV2(
                paired_response_schema_version=(
                    APPLICATION_PAIRED_RESPONSE_OUTCOME_V2_SCHEMA_VERSION
                ),
                authority_binding=authority,
                run_spec=run_spec,
                actual_endpoint_shell=shell,
                actual_response=actual,
                matched_ablated_response=matched,
                atomic_pair_sha=SHA0,
            )
        )


class ApplicationResponseV2SurfaceTests(unittest.TestCase):
    def test_exact_raw_and_opaque_contracts_are_exposed(self) -> None:
        from rulespace_v3.application_response import (
            ApplicationBranchSourceReadoutResponseV2,
            ApplicationEndpointReferenceV2,
            ApplicationEndpointShellV2,
            ApplicationPairedResponseOutcomeV2,
            ApplicationResponseAuthorityBindingV2,
            ApplicationResponseRunSpecV2,
            VerifiedApplicationBranchSourceReadoutResponseV2,
            VerifiedApplicationEndpointReferenceV2,
            VerifiedApplicationEndpointShellV2,
            VerifiedApplicationPairedResponseOutcomeV2,
        )

        for contract in (
            ApplicationResponseAuthorityBindingV2,
            ApplicationResponseRunSpecV2,
            ApplicationEndpointReferenceV2,
            ApplicationEndpointShellV2,
            ApplicationBranchSourceReadoutResponseV2,
            ApplicationPairedResponseOutcomeV2,
            VerifiedApplicationEndpointReferenceV2,
            VerifiedApplicationEndpointShellV2,
            VerifiedApplicationBranchSourceReadoutResponseV2,
            VerifiedApplicationPairedResponseOutcomeV2,
        ):
            self.assertIsInstance(contract.__name__, str)


class ApplicationResponseV2AuthorityContractTests(_Bodies, unittest.TestCase):
    def test_run_spec_and_authority_bind_full_v2_ancestry(self) -> None:
        from rulespace_v3.application_response import (
            verify_application_response_authority_binding_v2_body,
            verify_application_response_run_spec_v2_body,
        )

        run_spec = self._run_spec()
        authority = self._authority(run_spec)

        verified_run = verify_application_response_run_spec_v2_body(run_spec)
        verified_authority = verify_application_response_authority_binding_v2_body(
            authority,
            run_spec,
        )
        self.assertEqual(verified_run, run_spec)
        self.assertEqual(verified_authority, authority)
        self.assertIsNot(verified_run, run_spec)

        spliced = self._resign_authority(
            replace(authority, run_spec_sha=SHAF)
        )
        with self.assertRaisesRegex(ValueError, "run spec|lineage|splice"):
            verify_application_response_authority_binding_v2_body(
                spliced,
                run_spec,
            )


class ApplicationEndpointReferenceV2ContractTests(_Bodies, unittest.TestCase):
    def test_reference_is_actual_only_and_recursively_authority_bound(self) -> None:
        from rulespace_v3.application_response import (
            verify_application_endpoint_reference_v2_body,
        )

        reference = self._reference()
        verified = verify_application_endpoint_reference_v2_body(reference)

        self.assertEqual(verified, reference)
        self.assertIsNot(verified, reference)
        self.assertEqual(verified.branch, "actual")
        self.assertEqual(
            verified.actual_transition_sha,
            verified.authority_binding.actual_transition_sha,
        )

        with self.assertRaisesRegex(ValueError, "actual-only"):
            replace(reference, branch="matched_ablated")


class ApplicationEndpointShellV2ContractTests(_Bodies, unittest.TestCase):
    def test_shell_is_actual_only_and_nests_the_exact_reference(self) -> None:
        from rulespace_v3.application_response import (
            verify_application_endpoint_shell_v2_body,
        )

        shell = self._shell()
        verified = verify_application_endpoint_shell_v2_body(shell)

        self.assertEqual(verified, shell)
        self.assertEqual(
            verified.endpoint_reference.endpoint_reference_sha,
            shell.endpoint_reference.endpoint_reference_sha,
        )
        self.assertEqual(verified.branch, "actual")

        with self.assertRaisesRegex(ValueError, "actual-only"):
            replace(shell, branch="matched_ablated")

        other_run = self._resign_run_spec(
            replace(shell.run_spec, selected_fejer_order=512)
        )
        with self.assertRaisesRegex(ValueError, "run spec|splice"):
            self._resign_shell(replace(shell, run_spec=other_run))


class ApplicationPairedResponseV2ContractTests(_Bodies, unittest.TestCase):
    def test_pair_atomically_binds_both_branches_to_actual_shell_and_run(self) -> None:
        from rulespace_v3.application_response import (
            verify_application_paired_response_outcome_v2_body,
        )

        pair = self._pair()
        verified = verify_application_paired_response_outcome_v2_body(pair)

        self.assertEqual(verified, pair)
        self.assertEqual(verified.actual_response.branch, "actual")
        self.assertEqual(
            verified.matched_ablated_response.branch,
            "matched_ablated",
        )
        self.assertEqual(
            verified.actual_response.actual_endpoint_shell,
            verified.matched_ablated_response.actual_endpoint_shell,
        )
        self.assertEqual(
            verified.actual_response.run_spec,
            verified.matched_ablated_response.run_spec,
        )

        with self.assertRaisesRegex(ValueError, "branch|atomic|splice"):
            verify_application_paired_response_outcome_v2_body(
                self._resign_pair(
                    replace(
                        pair,
                        actual_response=pair.matched_ablated_response,
                        matched_ablated_response=pair.actual_response,
                    )
                )
            )

    def test_pair_rejects_different_jp_run_and_certificate_splices(self) -> None:
        from rulespace_v3.application_response import (
            verify_application_paired_response_outcome_v2_body,
        )
        from rulespace_v3.factory import freeze_complex_tensor

        pair = self._pair()
        swapped = freeze_complex_tensor(
            np.asarray(((0.0, 1.0), (1.0, 0.0)), dtype=np.complex128)
        )
        other_run = self._resign_run_spec(
            replace(pair.run_spec, source_injection_isometry=swapped)
        )
        hostile = object.__new__(type(pair.actual_response))
        for name, item in vars(pair.actual_response).items():
            object.__setattr__(hostile, name, item)
        object.__setattr__(hostile, "run_spec", other_run)
        hostile = self._resign_branch_response(hostile)
        resigned = self._resign_pair(replace(pair, actual_response=hostile))
        with self.assertRaisesRegex(ValueError, "run spec|J/P|splice"):
            verify_application_paired_response_outcome_v2_body(resigned)

        hostile_cert = object.__new__(type(pair.matched_ablated_response))
        for name, item in vars(pair.matched_ablated_response).items():
            object.__setattr__(hostile_cert, name, item)
        object.__setattr__(hostile_cert, "dynamics_certificate_sha", SHAF)
        hostile_cert = self._resign_branch_response(hostile_cert)
        resigned = self._resign_pair(
            replace(pair, matched_ablated_response=hostile_cert)
        )
        with self.assertRaisesRegex(ValueError, "certificate|authority|splice"):
            verify_application_paired_response_outcome_v2_body(resigned)


class ApplicationResponseV2OpaqueBoundaryTests(_Bodies, unittest.TestCase):
    def test_opaque_wrappers_reject_raw_forged_and_subclass_values(self) -> None:
        from rulespace_v3.application_response import (
            VerifiedApplicationBranchSourceReadoutResponseV2,
            VerifiedApplicationEndpointReferenceV2,
            VerifiedApplicationEndpointShellV2,
            VerifiedApplicationPairedResponseOutcomeV2,
            require_application_branch_source_readout_response_v2,
            require_application_endpoint_reference_v2,
            require_application_endpoint_shell_v2,
            require_application_paired_response_outcome_v2,
        )

        cases = (
            (
                VerifiedApplicationEndpointReferenceV2,
                require_application_endpoint_reference_v2,
                self._reference(),
            ),
            (
                VerifiedApplicationEndpointShellV2,
                require_application_endpoint_shell_v2,
                self._shell(),
            ),
            (
                VerifiedApplicationBranchSourceReadoutResponseV2,
                require_application_branch_source_readout_response_v2,
                self._branch_response("actual"),
            ),
            (
                VerifiedApplicationPairedResponseOutcomeV2,
                require_application_paired_response_outcome_v2,
                self._pair(),
            ),
        )
        for wrapper_type, require, raw in cases:
            with self.subTest(wrapper=wrapper_type.__name__):
                with self.assertRaises(TypeError):
                    wrapper_type()
                with self.assertRaises(TypeError):
                    require(raw)
                forged = object.__new__(wrapper_type)
                with self.assertRaises(ValueError):
                    require(forged)

                class Hostile(wrapper_type):
                    pass

                hostile = object.__new__(Hostile)
                with self.assertRaises(TypeError):
                    require(hostile)

    def test_public_issuers_accept_no_caller_numeric_or_branch_payloads(self) -> None:
        from rulespace_v3.application_response import (
            issue_v3m0_application_endpoint_reference_v2,
            issue_v3m0_application_endpoint_shell_v2,
            issue_v3m0_application_paired_response_v2,
        )

        endpoint_names = tuple(
            inspect.signature(
                issue_v3m0_application_endpoint_reference_v2
            ).parameters
        )
        self.assertEqual(
            endpoint_names,
            (
                "formal_parent_v2",
                "permit_v2",
                "materialization_v2",
                "protocol_v2",
                "actual_prestructure_v2",
                "matched_ablated_prestructure_v2",
                "actual_transition_v2",
                "matched_ablated_transition_v2",
                "actual_certificate_v2",
                "matched_ablated_certificate_v2",
                "qualification_v2",
            ),
        )
        self.assertEqual(
            tuple(
                inspect.signature(
                    issue_v3m0_application_endpoint_shell_v2
                ).parameters
            ),
            ("reference",),
        )
        self.assertEqual(
            tuple(
                inspect.signature(
                    issue_v3m0_application_paired_response_v2
                ).parameters
            ),
            ("shell",),
        )

    def test_public_chain_fails_closed_at_unwired_live_numeric_authority(self) -> None:
        from rulespace_v3.application_response import (
            ApplicationResponseV2UpstreamUnavailable,
            _replay_application_endpoint_reference_v2,
            issue_v3m0_application_endpoint_reference_v2,
        )

        inputs = (object(),) * 11
        with self.assertRaises(ApplicationResponseV2UpstreamUnavailable):
            _replay_application_endpoint_reference_v2(*inputs)
        with self.assertRaises(ApplicationResponseV2UpstreamUnavailable):
            issue_v3m0_application_endpoint_reference_v2(*inputs)


if __name__ == "__main__":
    unittest.main()
