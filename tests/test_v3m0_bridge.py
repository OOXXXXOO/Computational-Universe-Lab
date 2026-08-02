from __future__ import annotations

import builtins
import dataclasses
import inspect
from types import SimpleNamespace
import unittest
from unittest import mock

import mpmath as mp
import numpy as np

import rulespace_v3.bridge as bridge_module
import rulespace_v3.factory as factory_module
from rulespace_v3.ablation import matched_ablation
from rulespace_v3.bridge import (
    _preflight,
    audit_full_state_bridge,
    bridge_audit_payload,
    build_full_state_bridge_spec,
    full_state_bridge_spec_payload,
    generate_bridge_trial_vectors,
    verify_full_state_bridge_audit,
    verify_full_state_bridge_spec,
)
from rulespace_v3.dynamics import measure_transition
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import freeze_complex_tensor, frozen_tensor_array
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import issue_synthetic_prestructure_authority
from rulespace_v3.registry import build_closed_control_registry
from tests.test_v3m0_dynamics import _quarter_turn_controls


_LEGACY_BRIDGE_ALL = (
    "BRIDGE_AUDIT_SCHEMA_VERSION",
    "BRIDGE_KIND",
    "BRIDGE_MACRO_STEPS",
    "BRIDGE_SPEC_SCHEMA_VERSION",
    "BRIDGE_TOLERANCE",
    "TRIAL_DOMAIN_SEPARATOR",
    "TRIAL_GENERATION_ID",
    "TRIAL_GRAM_GATE_METHOD_ID",
    "BridgeAudit",
    "BridgeCaseAudit",
    "FullStateBridgeSpec",
    "audit_full_state_bridge",
    "bridge_audit_payload",
    "build_full_state_bridge_spec",
    "full_state_bridge_spec_payload",
    "generate_bridge_trial_vectors",
    "verify_full_state_bridge_audit",
    "verify_full_state_bridge_spec",
)


class BridgePrimitiveClosureTests(unittest.TestCase):
    def test_owner_neutral_cores_have_private_builtins(self):
        for core in (
            bridge_module._build_bound_full_state_bridge_spec,
            bridge_module._audit_full_state_bridge_from_raw,
        ):
            with self.subTest(core=core.__name__):
                self.assertIsNot(
                    core.__globals__["__builtins__"],
                    builtins.__dict__,
                )

    def test_dyadic_trials_ignore_shared_hashlib_and_math_rebinding(self):
        seed = bytes.fromhex("a" * 64)
        expected = bridge_module._odd_dyadic_component(seed, 17)
        with (
            mock.patch.object(
                bridge_module,
                "hashlib",
                SimpleNamespace(
                    sha256=mock.Mock(
                        side_effect=AssertionError(
                            "owner hashlib binding was consulted"
                        )
                    )
                ),
            ),
            mock.patch.object(
                bridge_module,
                "math",
                SimpleNamespace(
                    ldexp=mock.Mock(
                        side_effect=AssertionError("owner math binding was consulted")
                    )
                ),
            ),
        ):
            observed = bridge_module._odd_dyadic_component(seed, 17)
        self.assertEqual(observed, expected)


class FullStateBridgeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        cls.registry = build_closed_control_registry(
            cls.controls,
            cls.parent,
        )
        cls.construction = matched_ablation(cls.controls[0].factory)
        assert cls.construction.pair is not None
        cls.authority = issue_synthetic_prestructure_authority(
            cls.parent,
            cls.registry,
            "full",
            cls.construction,
            "actual",
        )
        cls.factory = cls.construction.pair.actual
        cls.transition = measure_transition(cls.factory, cls.authority)

    def test_spec_is_mechanical_and_has_no_observer_or_fejer_fields(self):
        spec = build_full_state_bridge_spec(
            self.factory,
            self.authority,
        )
        self.assertEqual(spec.macro_steps, (1, 2, 4))
        self.assertEqual(spec.bridge_grid.reciprocal_indices, ((0,),))
        np.testing.assert_array_equal(
            frozen_tensor_array(spec.state_trial_vectors),
            np.eye(2),
        )
        self.assertEqual(spec.trial_gram_frobenius_upper, 0.0)
        fields = {field.name for field in dataclasses.fields(spec)}
        self.assertNotIn("source_basis", fields)
        self.assertNotIn("readout_basis", fields)
        self.assertNotIn("fejer_order", fields)
        self.assertEqual(
            verify_full_state_bridge_spec(
                spec,
                self.factory,
                self.authority,
            ),
            spec,
        )

    def test_owner_neutral_bridge_cores_match_legacy_and_are_bound_once(self):
        spec = build_full_state_bridge_spec(
            self.factory,
            self.authority,
        )
        raw_transition = self.transition.transition
        direct_spec = bridge_module._build_bound_full_state_bridge_spec(
            self.factory,
            spec.bridge_grid,
            parent_freeze_sha=spec.parent_freeze_sha,
            prestructure_authority_sha=spec.prestructure_authority_sha,
        )
        direct_audit = bridge_module._audit_full_state_bridge_from_raw(
            raw_transition,
            self.factory,
            spec,
        )
        legacy_audit = audit_full_state_bridge(
            self.transition,
            self.factory,
            self.authority,
            spec,
        )

        self.assertEqual(direct_spec, spec)
        self.assertEqual(direct_audit, legacy_audit)
        self.assertEqual(
            spec.bridge_spec_sha,
            "f35581e587a86c066ea68382f676a4ffca07eb3986bd5ad02ef334aa6436d01a",
        )
        self.assertEqual(
            legacy_audit.bridge_sha,
            "e39a99b037baaefacba2c8cb1c9762d5ee59d9d9b929ee255904c9bc9fce1292",
        )
        spec_signature = inspect.signature(
            bridge_module._build_bound_full_state_bridge_spec
        )
        self.assertEqual(
            tuple(spec_signature.parameters),
            (
                "factory",
                "bridge_grid",
                "parent_freeze_sha",
                "prestructure_authority_sha",
            ),
        )
        self.assertTrue(
            all(
                spec_signature.parameters[name].kind
                is inspect.Parameter.POSITIONAL_OR_KEYWORD
                for name in ("factory", "bridge_grid")
            )
        )
        self.assertTrue(
            all(
                spec_signature.parameters[name].kind is inspect.Parameter.KEYWORD_ONLY
                for name in (
                    "parent_freeze_sha",
                    "prestructure_authority_sha",
                )
            )
        )
        self.assertEqual(str(spec_signature.return_annotation), "FullStateBridgeSpec")
        audit_signature = inspect.signature(
            bridge_module._audit_full_state_bridge_from_raw
        )
        self.assertEqual(
            tuple(audit_signature.parameters),
            ("transition", "factory", "spec"),
        )
        self.assertTrue(
            all(
                parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
                for parameter in audit_signature.parameters.values()
            )
        )
        self.assertEqual(str(audit_signature.return_annotation), "BridgeAudit")
        self.assertEqual(tuple(bridge_module.__all__), _LEGACY_BRIDGE_ALL)
        self.assertNotIn(
            "_build_bound_full_state_bridge_spec",
            bridge_module.__all__,
        )
        self.assertNotIn(
            "_audit_full_state_bridge_from_raw",
            bridge_module.__all__,
        )
        expected_spec_closure = tuple(
            cell.cell_contents
            for cell in (bridge_module._expected_spec.__closure__ or ())
        )
        expected_audit_closure = tuple(
            cell.cell_contents
            for cell in (bridge_module._expected_audit.__closure__ or ())
        )
        self.assertIn(
            bridge_module._build_bound_full_state_bridge_spec,
            expected_spec_closure,
        )
        self.assertIn(
            bridge_module._audit_full_state_bridge_from_raw,
            expected_audit_closure,
        )

        with mock.patch.object(
            bridge_module,
            "transition_symbol",
            side_effect=AssertionError("legacy verified symbol was consulted"),
            create=True,
        ):
            self.assertEqual(
                bridge_module._audit_full_state_bridge_from_raw(
                    raw_transition,
                    self.factory,
                    spec,
                ),
                direct_audit,
            )

    def test_legacy_bridge_joins_precede_exactly_one_raw_core_call(self):
        spec = build_full_state_bridge_spec(self.factory, self.authority)
        events = []

        def bind(factory, authority):
            events.append("authority-join")
            return bridge_module._bind_factory_authority(factory, authority)

        bound_core = mock.Mock(
            side_effect=lambda *args, **kwargs: (
                events.append("spec-core"),
                bridge_module._build_bound_full_state_bridge_spec(*args, **kwargs),
            )[1]
        )
        expected_spec = bridge_module._make_expected_spec(
            authority_binder=bind,
            support_builder=bridge_module._signed_support,
            grid_builder=bridge_module.build_bridge_grid_manifest,
            bound_spec_builder=bound_core,
        )
        self.assertEqual(expected_spec(self.factory, self.authority), spec)
        self.assertEqual(events, ["authority-join", "spec-core"])
        bound_core.assert_called_once()

        events.clear()

        def verify_spec(*args):
            events.append("spec-join")
            return verify_full_state_bridge_spec(*args)

        def verify_transition(value):
            events.append("transition-join")
            return bridge_module._reverify_verified_transition(value)

        audit_core = mock.Mock(
            side_effect=lambda *args: (
                events.append("audit-core"),
                bridge_module._audit_full_state_bridge_from_raw(*args),
            )[1]
        )
        expected_audit = bridge_module._make_expected_audit(
            spec_verifier=verify_spec,
            transition_reverifier=verify_transition,
            raw_audit_builder=audit_core,
        )
        self.assertEqual(
            expected_audit(
                self.transition,
                self.factory,
                self.authority,
                spec,
            ),
            audit_full_state_bridge(
                self.transition,
                self.factory,
                self.authority,
                spec,
            ),
        )
        self.assertEqual(events, ["spec-join", "transition-join", "audit-core"])
        audit_core.assert_called_once()

    def test_saved_bridge_audit_ignores_cross_owner_factory_redirect(self):
        spec = build_full_state_bridge_spec(self.factory, self.authority)
        raw_transition = self.transition.transition
        expected = bridge_module._audit_full_state_bridge_from_raw(
            raw_transition,
            self.factory,
            spec,
        )
        with mock.patch.object(
            factory_module,
            "_apply_primitive",
            side_effect=AssertionError("cross-owner factory redirect reached"),
        ) as redirected:
            observed = bridge_module._audit_full_state_bridge_from_raw(
                raw_transition,
                self.factory,
                spec,
            )
        redirected.assert_not_called()
        self.assertEqual(observed, expected)

    def test_saved_bridge_entrypoints_ignore_post_freeze_dispatch_redirects(self):
        saved_build = bridge_module.build_full_state_bridge_spec
        saved_audit = bridge_module.audit_full_state_bridge

        with mock.patch.object(
            bridge_module,
            "_expected_spec",
            return_value="BRIDGE_SPEC_PERMISSION_BYPASS",
        ) as redirected_spec:
            with self.assertRaises((TypeError, ValueError)):
                saved_build(object(), object())
        redirected_spec.assert_not_called()

        with mock.patch.object(
            bridge_module,
            "_expected_audit",
            return_value="BRIDGE_AUDIT_PERMISSION_BYPASS",
        ) as redirected_audit:
            with self.assertRaises((TypeError, ValueError)):
                saved_audit(object(), object(), object(), object())
        redirected_audit.assert_not_called()

    def test_saved_bridge_cores_ignore_post_freeze_builtin_shadows(self):
        spec = build_full_state_bridge_spec(
            self.factory,
            self.authority,
        )
        raw_transition = self.transition.transition
        expected_spec = bridge_module._build_bound_full_state_bridge_spec(
            self.factory,
            spec.bridge_grid,
            parent_freeze_sha=spec.parent_freeze_sha,
            prestructure_authority_sha=spec.prestructure_authority_sha,
        )
        expected_audit = bridge_module._audit_full_state_bridge_from_raw(
            raw_transition,
            self.factory,
            spec,
        )

        for name in ("len", "min"):
            with self.subTest(core="spec", name=name):
                with mock.patch.object(
                    bridge_module,
                    name,
                    side_effect=AssertionError(f"bridge.{name} was consulted"),
                    create=True,
                ) as redirected:
                    observed = bridge_module._build_bound_full_state_bridge_spec(
                        self.factory,
                        spec.bridge_grid,
                        parent_freeze_sha=spec.parent_freeze_sha,
                        prestructure_authority_sha=(spec.prestructure_authority_sha),
                    )
                redirected.assert_not_called()
                self.assertEqual(observed, expected_spec)

        for name in ("type", "zip", "enumerate", "range", "max"):
            with self.subTest(core="audit", name=name):
                with mock.patch.object(
                    bridge_module,
                    name,
                    side_effect=AssertionError(f"bridge.{name} was consulted"),
                    create=True,
                ) as redirected:
                    observed = bridge_module._audit_full_state_bridge_from_raw(
                        raw_transition,
                        self.factory,
                        spec,
                    )
                redirected.assert_not_called()
                self.assertEqual(observed, expected_audit)

    def test_saved_bridge_cores_ignore_shared_numpy_attribute_redirects(self):
        spec = build_full_state_bridge_spec(
            self.factory,
            self.authority,
        )
        raw_transition = self.transition.transition
        expected_audit = bridge_module._audit_full_state_bridge_from_raw(
            raw_transition,
            self.factory,
            spec,
        )
        redirected_eye = mock.Mock(
            side_effect=AssertionError("owner numpy.eye binding was consulted")
        )
        redirected_norm = mock.Mock(
            side_effect=AssertionError("owner numpy.linalg.norm binding was consulted")
        )
        redirected_numpy = SimpleNamespace(
            eye=redirected_eye,
            linalg=SimpleNamespace(norm=redirected_norm),
        )
        with mock.patch.object(bridge_module, "np", redirected_numpy):
            observed_spec = bridge_module._build_bound_full_state_bridge_spec(
                self.factory,
                spec.bridge_grid,
                parent_freeze_sha=spec.parent_freeze_sha,
                prestructure_authority_sha=spec.prestructure_authority_sha,
            )
        redirected_eye.assert_not_called()
        self.assertEqual(observed_spec, spec)

        with mock.patch.object(bridge_module, "np", redirected_numpy):
            observed_audit = bridge_module._audit_full_state_bridge_from_raw(
                raw_transition,
                self.factory,
                spec,
            )
        redirected_norm.assert_not_called()
        self.assertEqual(observed_audit, expected_audit)

    def test_bridge_replays_full_periodic_executor_for_every_case(self):
        spec = build_full_state_bridge_spec(
            self.factory,
            self.authority,
        )
        audit = audit_full_state_bridge(
            self.transition,
            self.factory,
            self.authority,
            spec,
        )
        self.assertEqual(len(audit.cases), 1 * 3 * 2)
        self.assertEqual(
            tuple(
                (case.reciprocal_index, case.macro_steps, case.trial_index)
                for case in audit.cases
            ),
            tuple(((0,), steps, trial) for steps in (1, 2, 4) for trial in range(2)),
        )
        self.assertLessEqual(audit.normalized_max, 1e-12)
        self.assertEqual(
            verify_full_state_bridge_audit(
                audit,
                self.transition,
                self.factory,
                self.authority,
                spec,
            ),
            audit,
        )

    def test_resigned_trial_or_audit_tamper_is_rejected(self):
        spec = build_full_state_bridge_spec(
            self.factory,
            self.authority,
        )
        changed_trials = frozen_tensor_array(spec.state_trial_vectors)
        changed_trials[0, 0] = 0.5
        changed_spec = dataclasses.replace(
            spec,
            state_trial_vectors=freeze_complex_tensor(changed_trials),
            bridge_spec_sha="0" * 64,
        )
        changed_spec = dataclasses.replace(
            changed_spec,
            bridge_spec_sha=canonical_sha(full_state_bridge_spec_payload(changed_spec)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_full_state_bridge_spec(
                changed_spec,
                self.factory,
                self.authority,
            )

        audit = audit_full_state_bridge(
            self.transition,
            self.factory,
            self.authority,
            spec,
        )
        first = dataclasses.replace(
            audit.cases[0],
            raw_abs_residual=0.5,
            normalized_residual=0.5,
        )
        changed_audit = dataclasses.replace(
            audit,
            cases=(first,) + audit.cases[1:],
            raw_abs_max=0.5,
            normalized_max=0.5,
            bridge_sha="0" * 64,
        )
        changed_audit = dataclasses.replace(
            changed_audit,
            bridge_sha=canonical_sha(bridge_audit_payload(changed_audit)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_full_state_bridge_audit(
                changed_audit,
                self.transition,
                self.factory,
                self.authority,
                spec,
            )
        missing = dataclasses.replace(
            audit,
            cases=audit.cases[:-1],
            bridge_sha="0" * 64,
        )
        missing = dataclasses.replace(
            missing,
            bridge_sha=canonical_sha(bridge_audit_payload(missing)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_full_state_bridge_audit(
                missing,
                self.transition,
                self.factory,
                self.authority,
                spec,
            )
        duplicate = dataclasses.replace(
            audit,
            cases=audit.cases + (audit.cases[-1],),
            bridge_sha="0" * 64,
        )
        duplicate = dataclasses.replace(
            duplicate,
            bridge_sha=canonical_sha(bridge_audit_payload(duplicate)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_full_state_bridge_audit(
                duplicate,
                self.transition,
                self.factory,
                self.authority,
                spec,
            )

        reordered = dataclasses.replace(
            audit,
            cases=tuple(reversed(audit.cases)),
            bridge_sha="0" * 64,
        )
        reordered = dataclasses.replace(
            reordered,
            bridge_sha=canonical_sha(bridge_audit_payload(reordered)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_full_state_bridge_audit(
                reordered,
                self.transition,
                self.factory,
                self.authority,
                spec,
            )

    def test_executor_resource_cap_is_checked_by_integer_preflight(self):
        with self.assertRaises((TypeError, ValueError)):
            _preflight(
                k_count=1,
                trial_count=1,
                state_count=1,
                spatial_shape=(600_000_000,),
                primitive_count=1,
            )


class DenseBridgeTrialTests(unittest.TestCase):
    def test_sha256_dense_trials_use_scalar_householder_and_are_orthonormal(self):
        with (
            mock.patch(
                "numpy.linalg.qr",
                side_effect=AssertionError("LAPACK QR is forbidden"),
            ),
            mock.patch(
                "numpy.linalg.svd",
                side_effect=AssertionError("LAPACK SVD is forbidden"),
            ),
            mock.patch(
                "numpy.linalg.eigh",
                side_effect=AssertionError("LAPACK eigh is forbidden"),
            ),
        ):
            tensor, upper = generate_bridge_trial_vectors(
                36,
                "a" * 64,
            )
        values = frozen_tensor_array(tensor)
        self.assertEqual(values.shape, (32, 36))
        with mp.workdps(100):
            total = mp.mpf("0")
            for first in range(32):
                for second in range(32):
                    entry = mp.mpc("0")
                    for state in range(36):
                        left = mp.mpc(
                            float(values[first, state].real),
                            float(values[first, state].imag),
                        )
                        right = mp.mpc(
                            float(values[second, state].real),
                            float(values[second, state].imag),
                        )
                        entry += left * mp.conj(right)
                    if first == second:
                        entry -= 1
                    total += abs(entry) ** 2
            independent = float(mp.sqrt(total))
        self.assertLessEqual(independent, upper)
        self.assertLessEqual(upper, 1e-12)
        again, again_upper = generate_bridge_trial_vectors(36, "a" * 64)
        self.assertEqual(again, tensor)
        self.assertEqual(again_upper, upper)
        q_columns = values.conj()
        for column in q_columns:
            nonzero = np.flatnonzero(column != 0.0)
            self.assertGreater(len(nonzero), 0)
            first = column[nonzero[0]]
            self.assertGreater(first.real, 0.0)
            self.assertEqual(first.imag, 0.0)

    def test_small_state_trials_are_bit_exact_identity(self):
        tensor, upper = generate_bridge_trial_vectors(4, "b" * 64)
        np.testing.assert_array_equal(
            frozen_tensor_array(tensor),
            np.eye(4),
        )
        self.assertEqual(upper, 0.0)


if __name__ == "__main__":
    unittest.main()
