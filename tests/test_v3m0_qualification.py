from __future__ import annotations

import dataclasses
import dis
import functools
import gc
import inspect
import unittest
import weakref
from types import SimpleNamespace
from unittest import mock

from rulespace_v3.ablation import matched_ablation
from rulespace_v3.bridge import build_full_state_bridge_spec
from rulespace_v3.certificate import (
    certify_transition_dynamics,
)
from rulespace_v3.contracts import BlockStatus
from rulespace_v3.dynamics import measure_transition
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.grids import build_dynamics_grid_manifest
from rulespace_v3.metric import build_stability_metric_witness
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import issue_synthetic_prestructure_authority
from rulespace_v3.qualification import (
    CertificateBackedQualificationEvidence,
    CertificateBackedQualificationOutcome,
    VerifiedCertificateBackedQualification,
    _reverify_verified_certificate_backed_qualification,
    certificate_backed_qualification_evidence_payload,
    certificate_backed_qualification_outcome_payload,
    qualify_ablation_from_certificate,
    verify_qualified_ablation_from_certificate,
)
from rulespace_v3.registry import build_closed_control_registry
from rulespace_v3.runtime import issue_runtime_evidence_manifest
from rulespace_v3.structure import build_structure_manifest
from tests.test_v3m0_dynamics import _quarter_turn_controls


class QualificationStructuralTests(unittest.TestCase):
    def test_oversized_raw_is_rejected_before_live_replay_or_hash(self):
        raw = object.__new__(CertificateBackedQualificationOutcome)
        object.__setattr__(raw, "status", BlockStatus(True, None))
        object.__setattr__(raw, "evidence", None)
        object.__setattr__(raw, "outcome_sha", "😀" * 5_000)

        with self.assertRaisesRegex(ValueError, "text.*resource cap"):
            verify_qualified_ablation_from_certificate(
                raw,
                object(),
                object(),
            )

    def test_non_utf8_surrogate_is_rejected_before_live_replay_or_hash(self):
        raw = object.__new__(CertificateBackedQualificationOutcome)
        object.__setattr__(raw, "status", BlockStatus(True, None))
        object.__setattr__(raw, "evidence", None)
        object.__setattr__(raw, "outcome_sha", "\ud800" * 64)

        with self.assertRaisesRegex(ValueError, "UTF-8"):
            verify_qualified_ablation_from_certificate(
                raw,
                object(),
                object(),
            )

    def test_oversized_container_precedes_nested_exact_type_dispatch(self):
        oversized = [None] * 8_388_609
        oversized[0] = object()
        raw = object.__new__(CertificateBackedQualificationOutcome)
        object.__setattr__(raw, "status", BlockStatus(True, None))
        object.__setattr__(raw, "evidence", None)
        object.__setattr__(raw, "outcome_sha", oversized)

        with self.assertRaisesRegex(ValueError, "body exceeds the resource cap"):
            verify_qualified_ablation_from_certificate(
                raw,
                object(),
                object(),
            )

    def test_invalid_presence_is_rejected_before_live_replay(self):
        raw = object.__new__(CertificateBackedQualificationOutcome)
        object.__setattr__(raw, "status", BlockStatus(True, None))
        object.__setattr__(raw, "evidence", None)
        object.__setattr__(raw, "outcome_sha", "0" * 64)

        with self.assertRaisesRegex(ValueError, "presence"):
            verify_qualified_ablation_from_certificate(
                raw,
                object(),
                object(),
            )

    def test_hostile_top_and_nested_subclasses_fail_before_getattribute(self):
        class HostileOutcome(CertificateBackedQualificationOutcome):
            def __getattribute__(self, name):
                raise RuntimeError(f"hostile top getter executed: {name}")

        with self.assertRaisesRegex(TypeError, "raw outcome"):
            verify_qualified_ablation_from_certificate(
                object.__new__(HostileOutcome),
                object(),
                object(),
            )

        class HostileEvidence(CertificateBackedQualificationEvidence):
            def __getattribute__(self, name):
                raise RuntimeError(f"hostile nested getter executed: {name}")

        raw = object.__new__(CertificateBackedQualificationOutcome)
        object.__setattr__(raw, "status", BlockStatus(True, None))
        object.__setattr__(raw, "evidence", object.__new__(HostileEvidence))
        object.__setattr__(raw, "outcome_sha", "0" * 64)
        with self.assertRaisesRegex(TypeError, "unsupported (exact )?type"):
            verify_qualified_ablation_from_certificate(
                raw,
                object(),
                object(),
            )

    def test_public_serializer_rejects_unknown_fields_and_invalid_presence(self):
        raw = object.__new__(CertificateBackedQualificationOutcome)
        object.__setattr__(raw, "status", BlockStatus(True, None))
        object.__setattr__(raw, "evidence", None)
        object.__setattr__(raw, "outcome_sha", "0" * 64)
        object.__setattr__(raw, "caller_unknown", True)

        with self.assertRaisesRegex(ValueError, "record fields differ"):
            certificate_backed_qualification_outcome_payload(raw)

        del raw.__dict__["caller_unknown"]
        with self.assertRaisesRegex(ValueError, "defined iff"):
            certificate_backed_qualification_outcome_payload(raw)

    def test_public_qualification_call_graph_has_no_local_global_loads(self):
        import rulespace_v3.qualification as qualification

        pending = [
            qualification.qualify_ablation_from_certificate,
            qualification.verify_qualified_ablation_from_certificate,
            VerifiedCertificateBackedQualification.outcome.fget,
        ]
        seen: set[int] = set()
        offenders: list[tuple[str, object]] = []
        while pending:
            function = pending.pop()
            if function is None or id(function) in seen:
                continue
            seen.add(id(function))
            if isinstance(function, functools.partial):
                pending.append(function.func)
                pending.extend(function.args)
                pending.extend((function.keywords or {}).values())
                continue
            if not inspect.isfunction(function):
                continue
            if function.__module__ == qualification.__name__:
                offenders.extend(
                    (function.__qualname__, instruction.argval)
                    for instruction in dis.get_instructions(function)
                    if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"}
                )
            reachable: list[object] = []
            reachable.extend(function.__defaults__ or ())
            reachable.extend((function.__kwdefaults__ or {}).values())
            reachable.extend(
                cell.cell_contents for cell in (function.__closure__ or ())
            )
            while reachable:
                value = reachable.pop()
                if inspect.isfunction(value):
                    pending.append(value)
                elif isinstance(value, functools.partial):
                    pending.append(value)
                elif type(value) in (tuple, list, frozenset):
                    reachable.extend(value)
                elif type(value) is dict:
                    reachable.extend(value.values())
        self.assertEqual(offenders, [])


class CertificateBackedQualificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        cls.registry = build_closed_control_registry(
            cls.controls,
            cls.parent,
        )
        cls.construction = matched_ablation(cls.controls[0].factory)
        assert cls.construction.pair is not None
        cls.ablated_factory = cls.construction.pair.ablated
        cls.actual_factory = cls.construction.pair.actual
        cls.authority = issue_synthetic_prestructure_authority(
            cls.parent,
            cls.registry,
            "full",
            cls.construction,
            "matched_ablated",
        )
        cls.transition = measure_transition(
            cls.ablated_factory,
            cls.authority,
        )
        cls.structure = build_structure_manifest(
            cls.ablated_factory,
            cls.authority,
        )
        cls.metric = build_stability_metric_witness(
            cls.ablated_factory,
            cls.authority,
            cls.structure,
        )
        cls.bridge_spec = build_full_state_bridge_spec(
            cls.ablated_factory,
            cls.authority,
        )
        cls.grid = build_dynamics_grid_manifest(
            cls.transition.transition.support_offsets,
            cls.metric.metric_support_offsets,
        )
        cls.runtime = issue_runtime_evidence_manifest()
        certified = certify_transition_dynamics(
            cls.ablated_factory,
            cls.transition,
            cls.authority,
            cls.structure,
            cls.metric,
            cls.bridge_spec,
            cls.grid,
            cls.runtime,
        )
        assert certified.certificate is not None
        cls.certificate = certified.certificate

    def _qualify(self):
        return qualify_ablation_from_certificate(
            self.construction,
            self.certificate,
        )

    def test_success_is_raw_serializable_and_hydrates_new_live_capability(self):
        verified = self._qualify()
        self.assertIs(type(verified), VerifiedCertificateBackedQualification)
        outcome = verified.outcome
        self.assertTrue(outcome.status.defined)
        self.assertIsNotNone(outcome.evidence)
        assert outcome.evidence is not None
        evidence = outcome.evidence
        self.assertTrue(evidence.construction_status.defined)
        self.assertEqual(
            evidence.dynamics_report.factory_sha,
            self.ablated_factory.factory.factory_sha,
        )
        self.assertTrue(evidence.dynamics_report.state_schema_matches)
        self.assertTrue(evidence.dynamics_report.reversible)
        self.assertTrue(evidence.dynamics_report.stable)
        self.assertEqual(
            evidence.verified_certificate_sha,
            self.certificate.certificate.certificate_sha,
        )
        self.assertEqual(
            evidence.evidence_sha,
            canonical_sha(certificate_backed_qualification_evidence_payload(evidence)),
        )
        self.assertEqual(
            outcome.outcome_sha,
            canonical_sha(certificate_backed_qualification_outcome_payload(outcome)),
        )

        hydrated = verify_qualified_ablation_from_certificate(
            outcome,
            self.construction,
            self.certificate,
        )
        self.assertIs(type(hydrated), VerifiedCertificateBackedQualification)
        self.assertIsNot(hydrated, verified)
        self.assertEqual(hydrated.outcome, outcome)

    def test_resigned_report_or_unknown_field_cannot_gain_authority(self):
        outcome = self._qualify().outcome
        assert outcome.evidence is not None
        report = dataclasses.replace(
            outcome.evidence.dynamics_report,
            stable=False,
            report_sha="0" * 64,
        )
        report = dataclasses.replace(
            report,
            report_sha=canonical_sha(
                {
                    "report_schema_version": report.report_schema_version,
                    "factory_sha": report.factory_sha,
                    "state_schema_matches": report.state_schema_matches,
                    "reversible": report.reversible,
                    "stable": report.stable,
                    "certificate_sha": report.certificate_sha,
                }
            ),
        )
        evidence = dataclasses.replace(
            outcome.evidence,
            dynamics_report=report,
            evidence_sha="0" * 64,
        )
        evidence = dataclasses.replace(
            evidence,
            evidence_sha=canonical_sha(
                certificate_backed_qualification_evidence_payload(evidence)
            ),
        )
        changed = dataclasses.replace(
            outcome,
            evidence=evidence,
            outcome_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            outcome_sha=canonical_sha(
                certificate_backed_qualification_outcome_payload(changed)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_qualified_ablation_from_certificate(
                changed,
                self.construction,
                self.certificate,
            )

        wrong_self_hash = dataclasses.replace(
            self._qualify().outcome,
            outcome_sha="0" * 64,
        )
        with self.assertRaisesRegex(ValueError, "self SHA"):
            verify_qualified_ablation_from_certificate(
                wrong_self_hash,
                object(),
                object(),
            )

        outcome = self._qualify().outcome
        assert outcome.evidence is not None
        object.__setattr__(
            outcome.evidence,
            "caller_stable",
            True,
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_qualified_ablation_from_certificate(
                outcome,
                self.construction,
                self.certificate,
            )

    def test_actual_certificate_or_different_construction_is_rejected(self):
        actual_authority = issue_synthetic_prestructure_authority(
            self.parent,
            self.registry,
            "full",
            self.construction,
            "actual",
        )
        actual_transition = measure_transition(
            self.actual_factory,
            actual_authority,
        )
        actual_structure = build_structure_manifest(
            self.actual_factory,
            actual_authority,
        )
        actual_metric = build_stability_metric_witness(
            self.actual_factory,
            actual_authority,
            actual_structure,
        )
        actual_spec = build_full_state_bridge_spec(
            self.actual_factory,
            actual_authority,
        )
        actual_grid = build_dynamics_grid_manifest(
            actual_transition.transition.support_offsets,
            actual_metric.metric_support_offsets,
        )
        certified = certify_transition_dynamics(
            self.actual_factory,
            actual_transition,
            actual_authority,
            actual_structure,
            actual_metric,
            actual_spec,
            actual_grid,
            issue_runtime_evidence_manifest(),
        )
        assert certified.certificate is not None
        with self.assertRaises((TypeError, ValueError)):
            qualify_ablation_from_certificate(
                self.construction,
                certified.certificate,
            )

        other = matched_ablation(self.controls[1].factory)
        with self.assertRaises((TypeError, ValueError)):
            verify_qualified_ablation_from_certificate(
                self._qualify().outcome,
                other,
                self.certificate,
            )

    def test_fake_slot_mutation_and_expired_identity_fail_closed(self):
        forged = object.__new__(VerifiedCertificateBackedQualification)
        with self.assertRaises((TypeError, ValueError)):
            _reverify_verified_certificate_backed_qualification(forged)

        verified = self._qualify()
        first = verified.outcome
        second = verified.outcome
        self.assertEqual(first, second)
        self.assertIsNot(first, second)
        assert first.evidence is not None
        object.__setattr__(
            first.evidence,
            "verified_certificate_sha",
            "0" * 64,
        )
        refreshed = _reverify_verified_certificate_backed_qualification(verified)
        self.assertEqual(refreshed.outcome, second)

        hidden = object.__getattribute__(
            verified,
            "_VerifiedCertificateBackedQualification__outcome",
        )
        assert hidden.evidence is not None
        object.__setattr__(
            hidden.evidence,
            "verified_certificate_sha",
            "0" * 64,
        )
        with self.assertRaises((TypeError, ValueError)):
            _reverify_verified_certificate_backed_qualification(verified)

        verified = self._qualify()
        reference = weakref.ref(verified)
        del verified
        gc.collect()
        self.assertIsNone(reference())

    def test_exact_public_record_surface(self):
        self.assertEqual(
            tuple(CertificateBackedQualificationEvidence.__dataclass_fields__),
            (
                "evidence_schema_version",
                "construction_status",
                "pair_snapshot",
                "dynamics_report",
                "verified_certificate_sha",
                "evidence_sha",
            ),
        )
        self.assertEqual(
            tuple(inspect.signature(qualify_ablation_from_certificate).parameters),
            ("construction", "ablated_certificate"),
        )
        self.assertEqual(
            tuple(
                inspect.signature(verify_qualified_ablation_from_certificate).parameters
            ),
            ("outcome", "construction", "ablated_certificate"),
        )

    def test_public_authority_boundaries_ignore_module_global_rebinding(self):
        import copy
        import json

        import rulespace_v3.qualification as qualification
        from rulespace_v3.parent_freeze import (
            V3M0SyntheticControlApplicationSpec,
        )

        expected = self._qualify().outcome
        with mock.patch.object(
            qualification,
            "_issue_verified_certificate_backed_qualification",
            side_effect=AssertionError("module-global issuer was consulted"),
        ):
            rebound_safe = qualify_ablation_from_certificate(
                self.construction,
                self.certificate,
            )
        self.assertEqual(rebound_safe.outcome, expected)

        with mock.patch.object(
            qualification,
            "_reverify_verified_certificate_backed_qualification",
            return_value=SimpleNamespace(
                outcome=dataclasses.replace(
                    expected,
                    outcome_sha="0" * 64,
                )
            ),
        ):
            self.assertEqual(rebound_safe.outcome, expected)

        with mock.patch.object(
            qualification,
            "_VerifiedQualificationView",
            return_value=SimpleNamespace(
                outcome=dataclasses.replace(
                    expected,
                    outcome_sha="0" * 64,
                )
            ),
        ):
            self.assertEqual(rebound_safe.outcome, expected)

        def shared_dispatch(*args, **kwargs):
            del args, kwargs
            raise AssertionError("shared deepcopy dispatch was consulted")

        with (
            mock.patch.object(
                json,
                "dumps",
                side_effect=AssertionError("shared json.dumps was consulted"),
            ),
            mock.patch.object(
                json,
                "JSONEncoder",
                side_effect=AssertionError("shared JSONEncoder was consulted"),
            ),
            mock.patch.dict(
                copy._deepcopy_dispatch,
                {V3M0SyntheticControlApplicationSpec: shared_dispatch},
            ),
        ):
            self.assertEqual(rebound_safe.outcome, expected)


if __name__ == "__main__":
    unittest.main()
