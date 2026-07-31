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
                reference_reciprocal_index=(run_spec.reference_reciprocal_index),
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
                projector=freeze_complex_tensor(np.eye(2, dtype=np.complex128)),
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
            self._reference(run_spec, authority) if reference is None else reference
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
                application_branch_source_readout_response_v2_payload(provisional)
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

    def _pair(self, *, run_spec=None, authority=None, shell=None):
        from rulespace_v3.application_response import (
            APPLICATION_PAIRED_RESPONSE_OUTCOME_V2_SCHEMA_VERSION,
            ApplicationPairedResponseOutcomeV2,
        )

        run_spec = self._run_spec() if run_spec is None else run_spec
        authority = self._authority(run_spec) if authority is None else authority
        shell = self._shell(run_spec, authority) if shell is None else shell
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

    def _pair_with_self_signed_unverified_shell(self, pair, shell):
        """Build the exact cross-splice attack without recursive helpers."""
        from rulespace_v3.application_response import (
            application_branch_source_readout_response_v2_payload,
            application_endpoint_shell_v2_payload,
            application_paired_response_outcome_v2_payload,
        )
        from rulespace_v3.evidence import canonical_sha

        shell_record = {
            **application_endpoint_shell_v2_payload(shell),
            "endpoint_shell_sha": shell.endpoint_shell_sha,
        }
        signed_branches = []
        branch_records = []
        for branch in (
            pair.actual_response,
            pair.matched_ablated_response,
        ):
            branch_payload = application_branch_source_readout_response_v2_payload(
                branch
            )
            branch_payload["actual_endpoint_shell"] = shell_record
            signed = replace(
                branch,
                actual_endpoint_shell=shell,
                branch_response_sha=canonical_sha(branch_payload),
            )
            signed_branches.append(signed)
            branch_records.append(
                {
                    **branch_payload,
                    "branch_response_sha": signed.branch_response_sha,
                }
            )

        pair_payload = application_paired_response_outcome_v2_payload(pair)
        pair_payload["actual_endpoint_shell"] = shell_record
        pair_payload["actual_response"] = branch_records[0]
        pair_payload["matched_ablated_response"] = branch_records[1]
        return replace(
            pair,
            actual_endpoint_shell=shell,
            actual_response=signed_branches[0],
            matched_ablated_response=signed_branches[1],
            atomic_pair_sha=canonical_sha(pair_payload),
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

    def test_module_exposes_no_mutable_live_tables_or_authority_seal(self) -> None:
        """数据完整性状态必须只存在于 factory closure。"""
        from weakref import WeakKeyDictionary

        import rulespace_v3.application_response as response_v2

        legacy_names = {
            "_REFERENCE_LIVE",
            "_SHELL_LIVE",
            "_BRANCH_RESPONSE_LIVE",
            "_PAIR_LIVE",
            "_AUTHORITY_SEAL",
        }
        exposed = vars(response_v2)
        self.assertTrue(legacy_names.isdisjoint(exposed))
        self.assertFalse(
            any(isinstance(value, WeakKeyDictionary) for value in exposed.values())
        )
        self.assertFalse(
            any(
                name.startswith(("hydrate_", "register_"))
                for name in response_v2.__all__
            )
        )


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

        spliced = self._resign_authority(replace(authority, run_spec_sha=SHAF))
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

    def test_reference_data_integrity_rejects_declared_rank_mismatch(self) -> None:
        """数据完整性要求 declared rank 与 projector 实秩对拍。"""
        from rulespace_v3.application_response import (
            verify_application_endpoint_reference_v2_body,
        )

        reference = self._reference()
        rank_splice = self._resign_reference(
            replace(reference, expected_shell_rank=1, rank=1)
        )

        with self.assertRaisesRegex(ValueError, "rank"):
            verify_application_endpoint_reference_v2_body(rank_splice)

    def test_tensor_data_integrity_rejects_list_shape_after_self_signing(
        self,
    ) -> None:
        """数据完整性要求 exact tensor 重放严格 wire post-init。"""
        from rulespace_v3.application_response import (
            verify_application_response_run_spec_v2_body,
        )
        from rulespace_v3.evidence import canonical_sha
        from rulespace_v3.factory import frozen_tensor_payload

        run_spec = self._run_spec()
        tensor = run_spec.source_injection_isometry
        object.__setattr__(tensor, "shape", [2, 2])
        object.__setattr__(
            tensor,
            "tensor_sha",
            canonical_sha(frozen_tensor_payload(tensor)),
        )

        with self.assertRaisesRegex(TypeError, "shape.*tuple"):
            verify_application_response_run_spec_v2_body(run_spec)


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

    def test_reference_row_cross_splices_rejected_by_shell_and_atomic_pair(
        self,
    ) -> None:
        """reference 行 phase/projector/participation 交叉拼接必须拒绝。"""
        from rulespace_v3.application_response import (
            verify_application_endpoint_shell_v2_body,
            verify_application_paired_response_outcome_v2_body,
        )
        from rulespace_v3.factory import freeze_complex_tensor

        run_spec = self._resign_run_spec(
            replace(
                self._run_spec(),
                reference_reciprocal_index=(1, 0),
            )
        )
        authority = self._authority(run_spec)
        reference = self._reference(run_spec, authority)
        shell = self._shell(run_spec, authority, reference)
        pair = self._pair(
            run_spec=run_spec,
            authority=authority,
            shell=shell,
        )

        projector_splice = np.stack(
            (
                np.eye(2, dtype=np.complex128),
                np.eye(2, dtype=np.complex128),
            )
        )
        projector_splice[1, 0, 1] = 1.0e-13
        projector_splice[1, 1, 0] = 1.0e-13
        splices = (
            (
                "phase",
                self._resign_shell(replace(shell, shell_phases=(0.25, 0.30))),
            ),
            (
                "projector",
                self._resign_shell(
                    replace(
                        shell,
                        shell_projectors=freeze_complex_tensor(projector_splice),
                    )
                ),
            ),
            (
                "participation",
                self._resign_shell(replace(shell, point_participations=(1.0, 0.75))),
            ),
        )
        for field, spliced_shell in splices:
            with self.subTest(field=field):
                spliced_pair = self._pair_with_self_signed_unverified_shell(
                    pair,
                    spliced_shell,
                )
                with self.assertRaisesRegex(
                    ValueError,
                    "reference row|cross-splice",
                ):
                    verify_application_endpoint_shell_v2_body(spliced_shell)
                with self.assertRaisesRegex(
                    ValueError,
                    "reference row|cross-splice",
                ):
                    verify_application_paired_response_outcome_v2_body(spliced_pair)


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
    def test_public_endpoint_boundaries_have_no_reachable_registry_or_seal(
        self,
    ) -> None:
        """Issuer/require 的递归依赖不得藏 registry 或 seal。"""
        from weakref import WeakKeyDictionary

        from rulespace_v3.application_response import (
            issue_v3m0_application_endpoint_reference_v2,
            require_application_endpoint_reference_v2,
        )

        violations = []
        seen = set()

        def walk(value, path):
            identity = id(value)
            if identity in seen:
                return
            seen.add(identity)
            if isinstance(value, WeakKeyDictionary):
                violations.append(f"{path}: live registry")
                return
            if not inspect.isfunction(value):
                return
            for name, cell in zip(
                value.__code__.co_freevars,
                value.__closure__ or (),
            ):
                if "seal" in name.lower():
                    violations.append(f"{path}: reachable seal {name}")
                walk(cell.cell_contents, f"{path}.closure[{name}]")
            for index, dependency in enumerate(value.__defaults__ or ()):
                walk(dependency, f"{path}.default[{index}]")
            for name, dependency in (value.__kwdefaults__ or {}).items():
                walk(dependency, f"{path}.kwdefault[{name}]")
            for name in value.__code__.co_names:
                dependency = value.__globals__.get(name)
                if inspect.isfunction(dependency):
                    walk(dependency, f"{path}.global[{name}]")

        walk(
            issue_v3m0_application_endpoint_reference_v2,
            "endpoint issuer",
        )
        walk(
            require_application_endpoint_reference_v2,
            "endpoint require",
        )
        self.assertEqual(violations, [])

    def test_reference_value_capability_replays_and_detects_slot_drift(
        self,
    ) -> None:
        """签发体内嵌完整 upstream；require 重放且拒绝改槽。"""
        from unittest.mock import patch

        import rulespace_v3.application_response as response_v2
        from rulespace_v3.application_response import (
            issue_v3m0_application_endpoint_reference_v2,
            require_application_endpoint_reference_v2,
        )

        issuer = issue_v3m0_application_endpoint_reference_v2
        issued_raw = self._reference()
        drifted_raw = self._resign_reference(replace(issued_raw, participation=0.75))
        replay_calls = []
        live_inputs = tuple(object() for _ in inspect.signature(issuer).parameters)

        def fixed_replayer(*live_upstream):
            replay_calls.append(live_upstream)
            if live_upstream != live_inputs:
                raise ValueError("upstream identity drifted")
            return issued_raw

        with patch.object(
            response_v2,
            "_replay_application_endpoint_reference_v2",
            fixed_replayer,
        ):
            capability = issuer(*live_inputs)
            self.assertEqual(
                require_application_endpoint_reference_v2(capability),
                issued_raw,
            )

            raw_slot = "_VerifiedApplicationEndpointReferenceV2__issued_raw"
            upstream_slot = "_VerifiedApplicationEndpointReferenceV2__live_upstream"
            object.__setattr__(capability, raw_slot, drifted_raw)
            with self.assertRaisesRegex(ValueError, "replay differs"):
                require_application_endpoint_reference_v2(capability)
            object.__setattr__(capability, raw_slot, issued_raw)
            object.__setattr__(
                capability,
                upstream_slot,
                live_inputs[:-1] + (object(),),
            )
            with self.assertRaisesRegex(ValueError, "upstream identity drifted"):
                require_application_endpoint_reference_v2(capability)

        self.assertEqual(len(replay_calls), 4)

    def test_reference_value_capability_rejects_missing_and_copied_slots(
        self,
    ) -> None:
        """object.__new__ 不能只靠自签 raw 或拷贝 raw 槽升级。"""
        from rulespace_v3.application_response import (
            VerifiedApplicationEndpointReferenceV2,
            require_application_endpoint_reference_v2,
        )

        raw_slot = "_VerifiedApplicationEndpointReferenceV2__issued_raw"
        upstream_slot = "_VerifiedApplicationEndpointReferenceV2__live_upstream"
        forged = object.__new__(VerifiedApplicationEndpointReferenceV2)
        with self.assertRaisesRegex(ValueError, "incomplete"):
            require_application_endpoint_reference_v2(forged)

        object.__setattr__(forged, raw_slot, self._reference())
        with self.assertRaisesRegex(ValueError, "incomplete"):
            require_application_endpoint_reference_v2(forged)

        object.__setattr__(forged, upstream_slot, (object(),) * 11)
        with self.assertRaises((TypeError, ValueError)):
            require_application_endpoint_reference_v2(forged)

    def test_exact_wrapper_data_integrity_resists_registry_and_global_redirects(
        self,
    ) -> None:
        """exact wrapper 不得借模块 registry 或 global lookup 交叉拼接。"""
        import rulespace_v3.application_response as response_v2

        wrapper = object.__new__(response_v2.VerifiedApplicationEndpointReferenceV2)
        raw = self._reference()
        with self.assertRaises(AttributeError):
            object.__setattr__(wrapper, "_authority_seal", object())
        with self.assertRaisesRegex(ValueError, "incomplete"):
            response_v2.require_application_endpoint_reference_v2(wrapper)

        original_require = response_v2.require_application_endpoint_reference_v2
        response_v2.require_application_endpoint_reference_v2 = lambda _: raw
        try:
            with self.assertRaisesRegex(ValueError, "incomplete"):
                _ = wrapper.reference
            with self.assertRaisesRegex(ValueError, "incomplete"):
                response_v2.issue_v3m0_application_endpoint_shell_v2(wrapper)
        finally:
            response_v2.require_application_endpoint_reference_v2 = original_require

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
            inspect.signature(issue_v3m0_application_endpoint_reference_v2).parameters
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
                inspect.signature(issue_v3m0_application_endpoint_shell_v2).parameters
            ),
            ("reference",),
        )
        self.assertEqual(
            tuple(
                inspect.signature(issue_v3m0_application_paired_response_v2).parameters
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
        with self.assertRaises(TypeError):
            _replay_application_endpoint_reference_v2(*inputs)
        with self.assertRaises(TypeError):
            issue_v3m0_application_endpoint_reference_v2(*inputs)
        self.assertTrue(
            issubclass(ApplicationResponseV2UpstreamUnavailable, RuntimeError)
        )


if __name__ == "__main__":
    unittest.main()
