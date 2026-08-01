"""Tests for the isolated, authority-neutral C19 10D refreeze preflight."""

from __future__ import annotations

from dataclasses import fields, replace
from contextlib import ExitStack
import math
import unittest
from unittest.mock import patch

import numpy as np


def _resign_preflight(preflight, **changes):
    from rulespace_v3.c19_refreeze import (
        c19_local_refreeze_preflight_payload,
    )
    from rulespace_v3.evidence import canonical_sha

    provisional = replace(preflight, **changes, preflight_sha="0" * 64)
    return replace(
        provisional,
        preflight_sha=canonical_sha(
            c19_local_refreeze_preflight_payload(provisional)
        ),
    )


def _resign_step(step, **changes):
    from rulespace_v3.c19_refreeze import c19_local_shear_step_payload
    from rulespace_v3.evidence import canonical_sha

    provisional = replace(step, **changes, step_sha="0" * 64)
    return replace(
        provisional,
        step_sha=canonical_sha(c19_local_shear_step_payload(provisional)),
    )


class C19LocalRefreezePreflightTests(unittest.TestCase):
    def test_builds_the_frozen_twenty_channel_local_program(self) -> None:
        from rulespace_v3.c19_refreeze import (
            C19_AUTHORITY_STATE,
            C19_CHANNEL_ORDER,
            C19_TARGET_TOOTH,
            build_c19_local_refreeze_preflight,
        )

        preflight = build_c19_local_refreeze_preflight()

        self.assertEqual(
            C19_CHANNEL_ORDER,
            tuple(
                channel
                for pair in range(10)
                for channel in (f"q{pair}", f"p{pair}")
            ),
        )
        self.assertEqual(preflight.authority_state, C19_AUTHORITY_STATE)
        self.assertEqual(preflight.channel_order, C19_CHANNEL_ORDER)
        self.assertEqual(preflight.spatial_ndim, 1)
        self.assertEqual(preflight.primitive_support_radius, 0)
        self.assertEqual(len(preflight.matched_steps), 30)
        self.assertEqual(len(preflight.actual_steps), 50)
        self.assertEqual(
            tuple(
                step
                for step in preflight.actual_steps
                if not step.target_conditioned
            ),
            preflight.matched_steps,
        )
        conditioned = tuple(
            step for step in preflight.actual_steps if step.target_conditioned
        )
        self.assertEqual(len(conditioned), 20)
        self.assertEqual(
            tuple(step.coefficient for step in conditioned),
            (C19_TARGET_TOOTH, -C19_TARGET_TOOTH) * 10,
        )
        self.assertTrue(
            all(step.offset == (0,) for step in preflight.actual_steps)
        )

    def test_executes_bit_exact_branch_neutral_j20_with_honest_digests(
        self,
    ) -> None:
        from rulespace_v3.c19_refreeze import (
            build_c19_local_refreeze_preflight,
            execute_c19_constant_symbol,
        )
        from rulespace_v3.factory import frozen_tensor_array

        preflight = build_c19_local_refreeze_preflight()
        j2 = np.asarray(((0.0, -1.0), (1.0, 0.0)), dtype=np.complex128)
        expected = np.zeros((20, 20), dtype=np.complex128)
        for pair in range(10):
            start = 2 * pair
            expected[start : start + 2, start : start + 2] = j2
        actual = frozen_tensor_array(preflight.actual_executed_kernel)
        matched = frozen_tensor_array(preflight.matched_executed_kernel)

        self.assertEqual(actual.tobytes(), expected.tobytes())
        self.assertEqual(matched.tobytes(), expected.tobytes())
        self.assertEqual(actual.tobytes(), matched.tobytes())
        self.assertEqual(
            preflight.actual_executed_kernel.tensor_sha,
            preflight.matched_executed_kernel.tensor_sha,
        )
        self.assertNotEqual(
            preflight.actual_program_digest,
            preflight.matched_program_digest,
        )
        self.assertNotEqual(
            preflight.actual_branch_digest,
            preflight.matched_branch_digest,
        )

        residuals = (
            preflight.actual_unitarity_residual,
            preflight.actual_symplectic_residual,
            preflight.actual_reality_residual,
            preflight.matched_unitarity_residual,
            preflight.matched_symplectic_residual,
            preflight.matched_reality_residual,
        )
        self.assertTrue(all(value <= 1.0e-12 for value in residuals))

        reference = None
        for lattice_size in (8, 16, 64):
            for reciprocal_index in ((0,), (1,), (2,), (7,)):
                for branch in ("actual", "matched_ablated"):
                    symbol = execute_c19_constant_symbol(
                        preflight,
                        branch=branch,
                        reciprocal_index=reciprocal_index,
                        lattice_size=lattice_size,
                    )
                    if reference is None:
                        reference = symbol.tobytes()
                    self.assertEqual(symbol.tobytes(), reference)

    def test_positive_frequency_source_and_readout_are_adjoint_partial_isometries(
        self,
    ) -> None:
        from rulespace_v3.c19_refreeze import (
            build_c19_local_refreeze_preflight,
        )
        from rulespace_v3.factory import frozen_tensor_array

        preflight = build_c19_local_refreeze_preflight()
        source = frozen_tensor_array(preflight.source_b_plus)
        readout = frozen_tensor_array(preflight.readout_b_plus_adjoint)

        self.assertEqual(source.shape, (20, 10))
        self.assertEqual(readout.shape, (10, 20))
        self.assertEqual(readout.tobytes(), source.conj().T.tobytes())
        with np.errstate(all="ignore"):
            np.testing.assert_allclose(
                source.conj().T @ source,
                np.eye(10, dtype=np.complex128),
                rtol=0.0,
                atol=1.0e-12,
            )
            np.testing.assert_allclose(
                readout @ readout.conj().T,
                np.eye(10, dtype=np.complex128),
                rtol=0.0,
                atol=1.0e-12,
            )
        self.assertLessEqual(preflight.source_isometry_residual, 1.0e-12)
        self.assertLessEqual(preflight.readout_coisometry_residual, 1.0e-12)

    def test_freezes_single_node_response_and_ten_dimensional_observer_geometry(
        self,
    ) -> None:
        from rulespace_v3.c19_refreeze import (
            build_c19_local_refreeze_preflight,
        )
        from rulespace_v3.factory import frozen_tensor_array

        preflight = build_c19_local_refreeze_preflight()
        self.assertEqual(preflight.response_torus_denominator, 8)
        self.assertEqual(preflight.response_reciprocal_indices, ((1,),))
        self.assertEqual(
            preflight.bridge_reciprocal_indices,
            ((0,), (1,), (7,)),
        )
        self.assertEqual(preflight.bridge_steps, (1, 2, 4))

        incidence = frozen_tensor_array(preflight.incidence_operator)
        tt_basis = frozen_tensor_array(preflight.tt_basis)
        gauge_basis = frozen_tensor_array(preflight.gauge_basis)
        row_basis = frozen_tensor_array(preflight.row_basis)
        ker_c = frozen_tensor_array(preflight.ker_c_projector)
        curvature = frozen_tensor_array(preflight.curvature_frame)
        principal = frozen_tensor_array(
            preflight.principal_sine_squared_kernel
        )

        expected_incidence = np.eye(10, dtype=np.complex128)[
            (0, 1, 6, 7, 8, 9),
            :,
        ]
        self.assertEqual(incidence.shape, (6, 10))
        self.assertEqual(incidence.tobytes(), expected_incidence.tobytes())
        self.assertEqual(tt_basis.shape, (10, 2))
        self.assertEqual(gauge_basis.shape, (10, 4))
        self.assertEqual(row_basis.shape, (10, 4))
        self.assertEqual(np.linalg.matrix_rank(incidence), 6)
        self.assertEqual(np.linalg.matrix_rank(gauge_basis), 4)
        complete = np.concatenate((tt_basis, gauge_basis, row_basis), axis=1)
        with np.errstate(all="ignore"):
            np.testing.assert_array_equal(incidence @ gauge_basis, 0.0)
            np.testing.assert_array_equal(
                complete.conj().T @ complete,
                np.eye(10, dtype=np.complex128),
            )
            np.testing.assert_array_equal(
                ker_c,
                complete[:, :6] @ complete[:, :6].conj().T,
            )
            np.testing.assert_array_equal(curvature, incidence.conj().T)
            expected_principal = (
                np.eye(6, dtype=np.complex128)
                - curvature.conj().T @ ker_c @ curvature
            )
        np.testing.assert_array_equal(principal, expected_principal)
        self.assertEqual(
            tuple(np.linalg.eigvalsh(principal)),
            (0.0, 0.0, 1.0, 1.0, 1.0, 1.0),
        )
        self.assertEqual(
            preflight.principal_spectrum,
            (0.0, 0.0, 1.0, 1.0, 1.0, 1.0),
        )

    def test_verifier_replays_complete_self_hash_and_rejects_caller_injection(
        self,
    ) -> None:
        from rulespace_v3.c19_refreeze import (
            build_c19_local_refreeze_preflight,
            c19_local_refreeze_preflight_payload,
            verify_c19_local_refreeze_preflight,
        )
        from rulespace_v3.evidence import canonical_sha

        preflight = build_c19_local_refreeze_preflight()
        self.assertIs(
            verify_c19_local_refreeze_preflight(preflight),
            preflight,
        )
        payload = c19_local_refreeze_preflight_payload(preflight)
        self.assertEqual(
            set(payload),
            {item.name for item in fields(type(preflight))}
            - {"preflight_sha"},
        )
        self.assertEqual(preflight.preflight_sha, canonical_sha(payload))

        injected = build_c19_local_refreeze_preflight()
        object.__setattr__(injected, "caller_unknown", "injected")
        with self.assertRaisesRegex(ValueError, "unknown|missing|field"):
            verify_c19_local_refreeze_preflight(injected)

        nested = build_c19_local_refreeze_preflight()
        object.__setattr__(nested.actual_steps[-1], "caller_unknown", "injected")
        with self.assertRaisesRegex(ValueError, "unknown|missing|field"):
            verify_c19_local_refreeze_preflight(nested)

    def test_rejects_four_dimensional_splice_and_second_response_node(
        self,
    ) -> None:
        from rulespace_v3.c19_refreeze import (
            build_c19_local_refreeze_preflight,
            verify_c19_local_refreeze_preflight,
        )

        preflight = build_c19_local_refreeze_preflight()
        four_dimensional = _resign_preflight(
            preflight,
            channel_order=("q0", "p0", "q1", "p1"),
        )
        with self.assertRaisesRegex(ValueError, "20|channel|ten-dimensional"):
            verify_c19_local_refreeze_preflight(four_dimensional)

        two_nodes = _resign_preflight(
            preflight,
            response_reciprocal_indices=((1,), (2,)),
        )
        with self.assertRaisesRegex(ValueError, "single|response|node"):
            verify_c19_local_refreeze_preflight(two_nodes)

    def test_rejects_old_phase_tooth_and_nonzero_support_offset(self) -> None:
        from rulespace_v3.c19_refreeze import (
            C19_TARGET_TOOTH,
            build_c19_local_refreeze_preflight,
            verify_c19_local_refreeze_preflight,
        )

        preflight = build_c19_local_refreeze_preflight()
        conditioned = tuple(
            step for step in preflight.actual_steps if step.target_conditioned
        )
        old_phase = (
            _resign_step(
                conditioned[-2],
                step_id="pair.09.conditioned.old-phase.lower.0",
                coefficient=float(math.tan(C19_TARGET_TOOTH / 2.0)),
            ),
            _resign_step(
                conditioned[-1],
                step_id="pair.09.conditioned.old-phase.upper",
                source_channel="p9",
                destination_channel="q9",
                coefficient=float(-math.sin(C19_TARGET_TOOTH)),
            ),
            _resign_step(
                conditioned[-2],
                step_id="pair.09.conditioned.old-phase.lower.1",
                coefficient=float(math.tan(C19_TARGET_TOOTH / 2.0)),
            ),
        )
        actual_without_last_inverse = preflight.actual_steps[:-2]
        attacked = _resign_preflight(
            preflight,
            actual_steps=(*actual_without_last_inverse, *old_phase),
        )
        with self.assertRaisesRegex(ValueError, "inverse|tooth|program"):
            verify_c19_local_refreeze_preflight(attacked)

        shifted = _resign_step(preflight.actual_steps[-1], offset=(1,))
        nonlocal_attack = _resign_preflight(
            preflight,
            actual_steps=(*preflight.actual_steps[:-1], shifted),
        )
        with self.assertRaisesRegex(ValueError, "offset|on-site|support"):
            verify_c19_local_refreeze_preflight(nonlocal_attack)

    def test_rejects_resigned_unequal_executed_kernels(self) -> None:
        from rulespace_v3.c19_refreeze import (
            build_c19_local_refreeze_preflight,
            verify_c19_local_refreeze_preflight,
        )
        from rulespace_v3.factory import freeze_complex_tensor

        preflight = build_c19_local_refreeze_preflight()
        unequal = _resign_preflight(
            preflight,
            actual_executed_kernel=freeze_complex_tensor(
                np.eye(20, dtype=np.complex128)
            ),
        )
        with self.assertRaisesRegex(ValueError, "kernel|branch-neutral|J20"):
            verify_c19_local_refreeze_preflight(unequal)

    def test_public_builder_and_verifier_ignore_all_module_rebinding(self) -> None:
        import rulespace_v3.c19_refreeze as c19

        builder = c19.build_c19_local_refreeze_preflight
        verifier = c19.verify_c19_local_refreeze_preflight
        baseline = builder()
        poisoned_calls = []

        def poison(label):
            def poisoned(*_, **__):
                poisoned_calls.append(label)
                raise AssertionError(f"rebound {label} was called")

            return poisoned

        rebound_values = {
            "C19_LOCAL_REFREEZE_PREFLIGHT_SCHEMA_VERSION": "forged.schema",
            "C19_LOCAL_SHEAR_STEP_SCHEMA_VERSION": "forged.step",
            "C19_AUTHORITY_STATE": "ISSUED",
            "C19_CHANNEL_ORDER": ("q0", "p0", "q1", "p1"),
            "C19_TARGET_TOOTH": 0.5,
        }
        helpers = (
            "_exact_record",
            "_step_record",
            "_tensor_record",
            "c19_local_shear_step_payload",
            "c19_local_refreeze_preflight_payload",
            "_step",
            "_pair_steps",
            "_execute_steps",
            "_program_digest",
            "_branch_digest",
            "_kernel_residuals",
            "_positive_frequency_bridge",
            "_bridge_residuals",
            "_observer_geometry",
            "_fp64_equal",
            "_canonical_j20",
            "_exact_text",
            "_exact_int",
            "_exact_float",
            "_exact_int_tuple",
            "_exact_index_tuple",
            "_sha",
            "_validate_preflight_wire_types",
            "canonical_sha",
            "freeze_complex_tensor",
            "frozen_tensor_array",
            "frozen_tensor_payload",
            "verify_frozen_tensor",
            "dataclass_fields",
        )
        with ExitStack() as stack:
            for name, value in rebound_values.items():
                stack.enter_context(patch.object(c19, name, value))
            for name in helpers:
                stack.enter_context(patch.object(c19, name, poison(name)))
            rebuilt = builder()
            self.assertEqual(rebuilt, baseline)
            self.assertIs(verifier(baseline), baseline)
        self.assertEqual(poisoned_calls, [])

    def test_verifier_rejects_bool_and_nonexact_numeric_wires(self) -> None:
        from rulespace_v3.c19_refreeze import (
            build_c19_local_refreeze_preflight,
            verify_c19_local_refreeze_preflight,
        )

        preflight = build_c19_local_refreeze_preflight()
        attacks = (
            {"spatial_ndim": True},
            {"primitive_support_radius": False},
            {"response_torus_denominator": True},
            {"response_reciprocal_indices": ((True,),)},
            {"bridge_reciprocal_indices": ((False,), (True,), (7,))},
            {"bridge_steps": (True, 2, 4)},
            {"principal_spectrum": (0, 0, 1, 1, 1, 1)},
        )
        for changes in attacks:
            with self.subTest(changes=changes):
                attacked = _resign_preflight(preflight, **changes)
                with self.assertRaises((TypeError, ValueError)):
                    verify_c19_local_refreeze_preflight(attacked)

        bool_offset = _resign_step(preflight.actual_steps[-1], offset=(False,))
        attacked = _resign_preflight(
            preflight,
            actual_steps=(*preflight.actual_steps[:-1], bool_offset),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_c19_local_refreeze_preflight(attacked)

    def test_executor_rejects_nonexact_lattice_and_momentum_wires(self) -> None:
        from rulespace_v3.c19_refreeze import (
            build_c19_local_refreeze_preflight,
            execute_c19_constant_symbol,
        )

        preflight = build_c19_local_refreeze_preflight()
        with self.assertRaises((TypeError, ValueError)):
            execute_c19_constant_symbol(
                preflight,
                branch="actual",
                reciprocal_index=(1,),
                lattice_size=8.0,
            )
        with self.assertRaises((TypeError, ValueError)):
            execute_c19_constant_symbol(
                preflight,
                branch="actual",
                reciprocal_index=(True,),
                lattice_size=8,
            )

    def test_verifier_rejects_damaged_top_step_and_tensor_hashes(self) -> None:
        from rulespace_v3.c19_refreeze import (
            build_c19_local_refreeze_preflight,
            verify_c19_local_refreeze_preflight,
        )

        preflight = build_c19_local_refreeze_preflight()
        with self.assertRaisesRegex(ValueError, "SHA|hash"):
            verify_c19_local_refreeze_preflight(
                replace(preflight, preflight_sha="f" * 64)
            )

        damaged_step = replace(preflight.actual_steps[-1], step_sha="f" * 64)
        with self.assertRaisesRegex(ValueError, "SHA|hash"):
            verify_c19_local_refreeze_preflight(
                replace(
                    preflight,
                    actual_steps=(*preflight.actual_steps[:-1], damaged_step),
                )
            )

        damaged_tensor = replace(
            preflight.actual_executed_kernel,
            tensor_sha="f" * 64,
        )
        with self.assertRaisesRegex(ValueError, "sha|SHA|hash"):
            verify_c19_local_refreeze_preflight(
                replace(preflight, actual_executed_kernel=damaged_tensor)
            )


if __name__ == "__main__":
    unittest.main()
