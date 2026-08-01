from __future__ import annotations

import dataclasses
import unittest
from unittest import mock

import numpy as np

from rulespace_v3.ablation import matched_ablation
from rulespace_v3.controls import (
    build_direct_sum_control,
    build_full_control,
    build_zero_control,
)
from rulespace_v3.dynamics import (
    MeasuredTransition,
    _allocate_transition_kernel,
    _assert_no_wrap,
    _assert_positive_bit_zero,
    _transition_symbol_from_raw,
    measure_transition,
    measured_transition_payload,
    transition_support_payload,
    transition_kernel_array,
    transition_symbol,
    verify_measured_transition,
)
from rulespace_v3.factory import (
    PrimitiveInterface,
    PrimitiveOperatorWire,
    VerifiedFactory,
    build_basis_manifest,
    build_calibration_seed,
    freeze_synthetic_target,
    freeze_complex_tensor,
    frozen_tensor_array,
    measure_calibration_holdout,
)
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.prestructure import (
    issue_synthetic_prestructure_authority,
    prestructure_authority_payload,
    verify_synthetic_prestructure_authority,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.registry import (
    VerifiedControlRegistry,
    build_closed_control_registry,
    closed_control_registry_payload,
    control_registry_entry_payload,
    verify_closed_control_registry,
)


_LEGACY_PARENT_SHA = "f57079846203b2cbcf86da7ebfb06c8d6bc55c5a2c16e2548e009d2a6ce607d9"
_LEGACY_SUPPORT_SHA = "c8733c2d64f71e9a917ffe4216ad17155da13784e44b1e51414aa8b1b8ab381f"
_LEGACY_KERNEL_SHA = "77427d534de8da171591920360a0f2f9baf6b1fec07574ebd05c7555d9b5c146"
_LEGACY_ROLE_GOLDENS = {
    "actual": {
        "factory_sha": (
            "215aede03b7f5a08d6d9061c4fd5c9db1c79ec7b50cd96d1d1c3cf453c221411"
        ),
        "prestructure_authority_sha": (
            "c899804ecd8937371837ca2f19545f38ec4dc415fa5b8ff88de2944ddacee9ea"
        ),
        "transition_sha": (
            "853477d539484505f92b459933d4532dc97d3c2a7a3204322a807b1a04a4a7ec"
        ),
    },
    "matched_ablated": {
        "factory_sha": (
            "b703ae19fda230949613b09593384d8fe6d9bcc6c4892e182551d7911b18fd33"
        ),
        "prestructure_authority_sha": (
            "662626c7494eb2e640c1778604caa814e5bfd4bc0a7f00719dceaf445d07bc4c"
        ),
        "transition_sha": (
            "2ad86d8645e79bbbec260722139f43852c73853c30b1d1e966f1b584e2e3ae7d"
        ),
    },
}


def _legacy_transition_payload_golden(role: str) -> dict[str, object]:
    role_golden = _LEGACY_ROLE_GOLDENS[role]
    values_wire = [[0.0, 0.0] for _ in range(20)]
    values_wire[5] = [-1.0, 0.0]
    values_wire[10] = [1.0, 0.0]
    return {
        "transition_schema_version": "v3m0.measured-transition.v1",
        "parent_freeze_sha": _LEGACY_PARENT_SHA,
        "prestructure_authority_sha": role_golden["prestructure_authority_sha"],
        "factory_sha": role_golden["factory_sha"],
        "factory_role": role,
        "state_schema_id": "state.synthetic.local-linear.v1",
        "channel_order": ["x.000", "y.000"],
        "spatial_shape": [5],
        "dt": 0.25,
        "boundary_manifest_id": "periodic-v1",
        "state_basis_convention_id": "channel-identity-v1",
        "kernel": {
            "tensor_schema_version": "v3m0.frozen-complex-tensor.v1",
            "shape": [2, 2, 5],
            "values_wire": values_wire,
            "tensor_sha": _LEGACY_KERNEL_SHA,
        },
        "support_offsets": [[0]],
        "support_sha": _LEGACY_SUPPORT_SHA,
        "macro_steps": 1,
    }


def _legacy_support_payload_golden() -> dict[str, object]:
    return {
        "support_schema_version": "v3m0.transition-support.v1",
        "support_offsets": [[0]],
        "spatial_shape": [5],
        "channel_order": ["x.000", "y.000"],
        "state_basis_convention_id": "channel-identity-v1",
        "origin_convention_id": "periodic-index-zero-origin-v1",
    }


def _quarter_turn_controls():
    shape = (5,)
    interface = PrimitiveInterface(
        interface_id="interface.synthetic.local-linear.v1",
        state_schema_id="state.synthetic.local-linear.v1",
        spatial_ndim=1,
        channel_order=("x.000", "y.000"),
        dtype="complex128",
        backend="numpy",
    )
    source = build_basis_manifest(
        role="source",
        state_schema_id=interface.state_schema_id,
        channel_order=interface.channel_order,
        vectors=np.asarray(((1.0, 0.0),), dtype=np.complex128),
    )
    holdout = build_basis_manifest(
        role="holdout_source",
        state_schema_id=interface.state_schema_id,
        channel_order=interface.channel_order,
        vectors=np.asarray(((1.0, 0.0),), dtype=np.complex128),
    )
    readout = build_basis_manifest(
        role="readout",
        state_schema_id=interface.state_schema_id,
        channel_order=interface.channel_order,
        vectors=np.asarray(((0.0, 1.0),), dtype=np.complex128),
    )
    coefficients = (1.0, -1.0, 1.0)
    sources = ("x.000", "y.000", "x.000")
    destinations = ("y.000", "x.000", "y.000")
    operators = tuple(
        PrimitiveOperatorWire(
            mechanism_id=f"pair.000.shear.{layer}",
            production_id="local_canonical_shear",
            layer_slot_id=f"layer.000.{layer}",
            operation_id="local_canonical_shear",
            interface_id=interface.interface_id,
            source_channel=sources[layer],
            destination_channel=destinations[layer],
            offset=(0,),
            coefficient_wire=(coefficients[layer], 0.0),
        )
        for layer in range(3)
    )
    seed = build_calibration_seed(
        calibration_protocol_id="calibration.synthetic.v1",
        interface=interface,
        state_shape=(2,) + shape,
        dt=0.25,
        target_blind_parameters=(("mass", 1.0),),
        source_basis=source,
        holdout_source_basis=holdout,
        readout_basis=readout,
        boundary_manifest_id="periodic-v1",
        operator_payload=operators,
    )
    observation = measure_calibration_holdout(seed)
    target = freeze_synthetic_target(
        seed,
        observation,
        "target.synthetic.v1",
    )
    return (
        build_full_control(seed, observation, target),
        build_zero_control(1, target, shape, 0.25),
        build_direct_sum_control(1, target, shape, 0.25),
    )


class FullStateTransitionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = issue_v3m0_parent_freeze()
        cls.controls = _quarter_turn_controls()
        cls.registry = build_closed_control_registry(
            cls.controls,
            cls.parent,
        )

    def _role_transition(self, control_index, role):
        control = self.controls[control_index]
        construction = matched_ablation(control.factory)
        self.assertTrue(construction.status.defined)
        self.assertIsNotNone(construction.pair)
        authority = issue_synthetic_prestructure_authority(
            self.parent,
            self.registry,
            control.control_id,
            construction,
            role,
        )
        assert construction.pair is not None
        factory = (
            construction.pair.actual if role == "actual" else construction.pair.ablated
        )
        transition = measure_transition(factory, authority)
        return construction, authority, factory, transition

    def test_registry_is_closed_ordered_and_replay_hydrated(self):
        raw = self.registry.registry
        self.assertEqual(
            tuple(entry.control_id for entry in raw.entries),
            ("full", "zero", "direct_sum"),
        )
        for control, entry in zip(self.controls, raw.entries):
            self.assertEqual(entry.expected_h_actual_rank, control.expected_actual_rank)
            self.assertEqual(
                entry.expected_h_ablated_rank, control.expected_ablated_rank
            )
            self.assertEqual(
                entry.expected_curv_actual_rank,
                control.expected_actual_rank,
            )
            self.assertEqual(
                entry.expected_curv_ablated_rank,
                control.expected_ablated_rank,
            )
            spec = entry.readout_calibration_spec
            np.testing.assert_array_equal(
                frozen_tensor_array(spec.h_metric_whitener),
                np.eye(len(entry.readout_basis.vectors_wire)),
            )
            np.testing.assert_array_equal(
                frozen_tensor_array(spec.curvature_incidence_operator),
                np.eye(len(entry.readout_basis.vectors_wire)),
            )
        hydrated = verify_closed_control_registry(
            raw,
            self.controls,
            self.parent,
        )
        self.assertEqual(hydrated.registry, raw)

        changed_entry = dataclasses.replace(
            raw.entries[0],
            builder_id="caller-resigned-builder",
            entry_sha="0" * 64,
        )
        changed_entry = dataclasses.replace(
            changed_entry,
            entry_sha=canonical_sha(control_registry_entry_payload(changed_entry)),
        )
        changed_registry = dataclasses.replace(
            raw,
            entries=(changed_entry,) + raw.entries[1:],
            registry_sha="0" * 64,
        )
        changed_registry = dataclasses.replace(
            changed_registry,
            registry_sha=canonical_sha(
                closed_control_registry_payload(changed_registry)
            ),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_closed_control_registry(
                changed_registry,
                self.controls,
                self.parent,
            )

        forged = object.__new__(VerifiedControlRegistry)
        construction = matched_ablation(self.controls[0].factory)
        with self.assertRaises((TypeError, ValueError)):
            issue_synthetic_prestructure_authority(
                self.parent,
                forged,
                "full",
                construction,
                "actual",
            )
        changed_controls = (
            dataclasses.replace(
                self.controls[0],
                expected_actual_rank=999,
            ),
        ) + self.controls[1:]
        with self.assertRaises((TypeError, ValueError)):
            build_closed_control_registry(changed_controls, self.parent)

    def test_prestructure_snapshot_is_serializable_and_role_specific(self):
        construction = matched_ablation(self.controls[0].factory)
        authority = issue_synthetic_prestructure_authority(
            self.parent,
            self.registry,
            "full",
            construction,
            "actual",
        )
        raw = authority.authority
        snapshot = raw.ablation_pair_snapshot
        self.assertNotIsInstance(snapshot.actual_factory, VerifiedFactory)
        self.assertNotIsInstance(snapshot.ablated_factory, VerifiedFactory)
        self.assertEqual(raw.factory_sha, snapshot.actual_factory.factory_sha)
        structure = frozen_tensor_array(raw.synthetic_preregistration.structure_form)
        np.testing.assert_array_equal(structure.T, -structure)
        hydrated = verify_synthetic_prestructure_authority(
            raw,
            self.parent,
            self.registry,
            "full",
            construction,
            "actual",
        )
        self.assertEqual(hydrated.authority, raw)

        changed = dataclasses.replace(
            raw,
            synthetic_registry_entry_sha=(self.registry.registry.entries[1].entry_sha),
            authority_sha="0" * 64,
        )
        changed = dataclasses.replace(
            changed,
            authority_sha=canonical_sha(prestructure_authority_payload(changed)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_synthetic_prestructure_authority(
                changed,
                self.parent,
                self.registry,
                "full",
                construction,
                "actual",
            )

    def test_realspace_impulses_measure_square_full_state_transition(self):
        _, authority, factory, transition = self._role_transition(0, "actual")
        raw = transition.transition
        self.assertEqual(raw.factory_role, "actual")
        self.assertEqual(raw.factory_sha, authority.factory_sha)
        self.assertEqual(raw.channel_order, ("x.000", "y.000"))
        self.assertEqual(raw.spatial_shape, (5,))
        self.assertEqual(raw.support_offsets, ((0,),))
        kernel = transition_kernel_array(transition)
        self.assertEqual(kernel.shape, (2, 2, 5))
        np.testing.assert_array_equal(
            kernel[:, :, 0],
            np.asarray(((0.0, -1.0), (1.0, 0.0))),
        )
        np.testing.assert_array_equal(kernel[:, :, 1:], 0.0)
        verified = verify_measured_transition(raw, factory, authority)
        self.assertEqual(verified.transition, raw)

    def test_legacy_actual_and_matched_full_payload_sha_support_goldens(self):
        for role in ("actual", "matched_ablated"):
            with self.subTest(role=role):
                _, _, _, transition = self._role_transition(0, role)
                raw = transition.transition
                payload = measured_transition_payload(raw)
                expected_payload = _legacy_transition_payload_golden(role)
                self.assertEqual(payload, expected_payload)
                self.assertEqual(
                    canonical_sha(payload),
                    _LEGACY_ROLE_GOLDENS[role]["transition_sha"],
                )
                self.assertEqual(
                    raw.transition_sha,
                    _LEGACY_ROLE_GOLDENS[role]["transition_sha"],
                )
                support_payload = transition_support_payload(
                    raw.support_offsets,
                    raw.spatial_shape,
                    raw.channel_order,
                    raw.state_basis_convention_id,
                )
                self.assertEqual(
                    support_payload,
                    _legacy_support_payload_golden(),
                )
                self.assertEqual(canonical_sha(support_payload), _LEGACY_SUPPORT_SHA)
                self.assertEqual(raw.support_sha, _LEGACY_SUPPORT_SHA)
                self.assertEqual(raw.kernel.tensor_sha, _LEGACY_KERNEL_SHA)

    def test_legacy_join_precedes_exactly_one_shared_core_call(self):
        import rulespace_v3.dynamics as dynamics

        construction = matched_ablation(self.controls[0].factory)
        self.assertTrue(construction.status.defined)
        assert construction.pair is not None
        authority = issue_synthetic_prestructure_authority(
            self.parent,
            self.registry,
            "full",
            construction,
            "actual",
        )
        factory = construction.pair.actual
        shared_core = dynamics._measure_bound_realspace_transition

        with (
            mock.patch.object(
                dynamics,
                "_bind_inputs",
                side_effect=ValueError("legacy join rejected"),
            ) as bind_inputs,
            mock.patch.object(
                dynamics,
                "_measure_bound_realspace_transition",
                wraps=shared_core,
            ) as core,
        ):
            with self.assertRaisesRegex(ValueError, "legacy join rejected"):
                dynamics._remeasure_transition(factory, authority)
        bind_inputs.assert_called_once_with(factory, authority)
        core.assert_not_called()

        call_order: list[str] = []
        original_bind_inputs = dynamics._bind_inputs

        def traced_bind_inputs(*args, **kwargs):
            call_order.append("bind")
            return original_bind_inputs(*args, **kwargs)

        def traced_core(*args, **kwargs):
            call_order.append("core")
            return shared_core(*args, **kwargs)

        with (
            mock.patch.object(
                dynamics,
                "_bind_inputs",
                side_effect=traced_bind_inputs,
            ) as bind_inputs,
            mock.patch.object(
                dynamics,
                "_measure_bound_realspace_transition",
                side_effect=traced_core,
            ) as core,
        ):
            raw = dynamics._remeasure_transition(factory, authority)
        bind_inputs.assert_called_once_with(factory, authority)
        core.assert_called_once_with(
            factory,
            parent_freeze_sha=_LEGACY_PARENT_SHA,
            prestructure_authority_sha=(
                _LEGACY_ROLE_GOLDENS["actual"]["prestructure_authority_sha"]
            ),
        )
        self.assertEqual(call_order, ["bind", "core"])
        self.assertEqual(
            measured_transition_payload(raw),
            _legacy_transition_payload_golden("actual"),
        )
        self.assertEqual(
            raw.transition_sha,
            _LEGACY_ROLE_GOLDENS["actual"]["transition_sha"],
        )

    def test_matched_ablated_role_is_bound_before_measurement(self):
        construction, actual_authority, actual_factory, _ = self._role_transition(
            1, "actual"
        )
        assert construction.pair is not None
        ablated_authority = issue_synthetic_prestructure_authority(
            self.parent,
            self.registry,
            "zero",
            construction,
            "matched_ablated",
        )
        ablated = measure_transition(
            construction.pair.ablated,
            ablated_authority,
        )
        np.testing.assert_array_equal(
            transition_kernel_array(ablated)[:, :, 0],
            np.eye(2),
        )
        with self.assertRaises((TypeError, ValueError)):
            measure_transition(actual_factory, ablated_authority)
        with self.assertRaises((TypeError, ValueError)):
            verify_measured_transition(
                ablated.transition,
                actual_factory,
                actual_authority,
            )

    def test_transition_symbol_uses_verified_full_kernel(self):
        _, _, _, transition = self._role_transition(0, "actual")
        expected = np.asarray(((0.0, -1.0), (1.0, 0.0)))
        for momentum in (0.0, 0.4, -2.1):
            np.testing.assert_allclose(
                transition_symbol(
                    transition,
                    np.asarray((momentum,), dtype=np.float64),
                ),
                expected,
                rtol=0.0,
                atol=0.0,
            )
        with self.assertRaises((TypeError, ValueError)):
            transition_symbol(
                transition.transition,
                np.asarray((0.0,), dtype=np.float64),
            )

    def test_signed_support_fourier_phase_is_exp_minus_i_k_dot_d(self):
        kernel = np.zeros((1, 1, 5), dtype=np.complex128)
        kernel[0, 0, 1] = 1.0
        raw = MeasuredTransition(
            transition_schema_version="v3m0.measured-transition.v1",
            parent_freeze_sha="0" * 64,
            prestructure_authority_sha="0" * 64,
            factory_sha="0" * 64,
            factory_role="actual",
            state_schema_id="state.phase-test.v1",
            channel_order=("z",),
            spatial_shape=(5,),
            dt=1.0,
            boundary_manifest_id="periodic-v1",
            state_basis_convention_id="channel-identity-v1",
            kernel=freeze_complex_tensor(kernel),
            support_offsets=((1,),),
            support_sha=canonical_sha(
                transition_support_payload(
                    ((1,),),
                    (5,),
                    ("z",),
                    "channel-identity-v1",
                )
            ),
            macro_steps=1,
            transition_sha="0" * 64,
        )
        momentum = np.asarray((0.4,), dtype=np.float64)
        np.testing.assert_allclose(
            _transition_symbol_from_raw(raw, momentum),
            np.asarray(((np.exp(-0.4j),),)),
            rtol=0.0,
            atol=0.0,
        )

    def test_no_wrap_and_positive_zero_are_bit_level_gates(self):
        _assert_no_wrap((3,), ((-1,), (0,), (1,)))
        with self.assertRaises((TypeError, ValueError)):
            _assert_no_wrap((2,), ((-1,), (0,), (1,)))
        _assert_positive_bit_zero(np.asarray((0.0 + 0.0j,), dtype=np.complex128))
        negative_zero = np.asarray(
            (complex(-0.0, 0.0),),
            dtype=np.complex128,
        )
        with self.assertRaises((TypeError, ValueError)):
            _assert_positive_bit_zero(negative_zero)

    def test_raw_self_hash_cannot_replace_executor_remeasurement(self):
        _, authority, factory, transition = self._role_transition(0, "actual")
        raw = transition.transition
        tampered_kernel = transition_kernel_array(transition)
        tampered_kernel[0, 0, 0] = 0.5
        tampered = dataclasses.replace(
            raw,
            kernel=freeze_complex_tensor(tampered_kernel),
            transition_sha="0" * 64,
        )
        tampered = dataclasses.replace(
            tampered,
            transition_sha=canonical_sha(measured_transition_payload(tampered)),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_measured_transition(tampered, factory, authority)

    def test_transition_cap_rejects_before_numpy_allocation(self):
        with mock.patch(
            "rulespace_v3.dynamics.np.zeros",
            side_effect=AssertionError("allocation must not occur"),
        ) as allocator:
            with self.assertRaises((TypeError, ValueError)):
                _allocate_transition_kernel(
                    4096,
                    (2,),
                )
        allocator.assert_not_called()


if __name__ == "__main__":
    unittest.main()
