from __future__ import annotations

import concurrent.futures
import dataclasses
import gc
import inspect
import threading
import unittest
import weakref
from unittest import mock

import numpy as np
import sympy as sp

from rulespace_v3.ablation import (
    AblationConstructionOutcome,
    AblationDynamicsReport,
    QualifiedAblationOutcome,
    VerifiedDynamicsReport,
    ablation_manifest_payload,
    dynamics_report_payload,
    matched_ablation,
    qualify_ablation,
    verify_ablation_pair,
    verify_qualified_ablation,
    verify_verified_dynamics_report,
)
from rulespace_v3.contracts import BlockStatus, UndefinedReason
from rulespace_v3.controls import (
    build_direct_sum_control,
    build_full_control,
    build_zero_control,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import (
    PrimitiveInterface,
    PrimitiveOperatorWire,
    VerifiedFactory,
    apply_factory_step,
    basis_manifest_array,
    basis_manifest_payload,
    build_basis_manifest,
    build_calibration_seed,
    build_factory_from_trace,
    build_full_factory_from_seed,
    calibration_observation_payload,
    calibration_seed_payload,
    factory_payload,
    factory_sha,
    factory_support_offsets,
    freeze_complex_tensor,
    freeze_synthetic_target,
    frozen_tensor_array,
    frozen_tensor_payload,
    measure_calibration_holdout,
    primitive_operator_payload,
    runtime_operator_sha,
    synthetic_target_payload,
    verify_basis_manifest,
    verify_factory,
    verify_frozen_tensor,
    verify_synthetic_target,
)
from rulespace_v3.trace import (
    PrimitiveSpec,
    ProvenanceNode,
    ProvenanceOperation,
    build_construction_trace,
)


SHA_A = "a" * 64


def interface_for(channels, ndim=1):
    return PrimitiveInterface(
        interface_id="interface.synthetic.v1",
        state_schema_id="state.synthetic.v1",
        spatial_ndim=ndim,
        channel_order=tuple(channels),
        dtype="complex128",
        backend="numpy",
    )


def basis(role, interface, vectors):
    return build_basis_manifest(
        role=role,
        state_schema_id=interface.state_schema_id,
        channel_order=interface.channel_order,
        vectors=np.asarray(vectors, dtype=np.complex128),
    )


def quarter_turn_operator(interface):
    return (
        PrimitiveOperatorWire(
            mechanism_id="m0",
            production_id="local_canonical_shear",
            layer_slot_id="slot.0",
            operation_id="local_canonical_shear",
            interface_id=interface.interface_id,
            source_channel=interface.channel_order[0],
            destination_channel=interface.channel_order[1],
            offset=(0,) * interface.spatial_ndim,
            coefficient_wire=(1.0, 0.0),
        ),
        PrimitiveOperatorWire(
            mechanism_id="m1",
            production_id="local_canonical_shear",
            layer_slot_id="slot.1",
            operation_id="local_canonical_shear",
            interface_id=interface.interface_id,
            source_channel=interface.channel_order[1],
            destination_channel=interface.channel_order[0],
            offset=(0,) * interface.spatial_ndim,
            coefficient_wire=(-1.0, 0.0),
        ),
        PrimitiveOperatorWire(
            mechanism_id="m2",
            production_id="local_canonical_shear",
            layer_slot_id="slot.2",
            operation_id="local_canonical_shear",
            interface_id=interface.interface_id,
            source_channel=interface.channel_order[0],
            destination_channel=interface.channel_order[1],
            offset=(0,) * interface.spatial_ndim,
            coefficient_wire=(1.0, 0.0),
        ),
    )


def seed_target(spatial_shape=(9,)):
    interface = interface_for(("x.000", "y.000"), len(spatial_shape))
    source = basis("source", interface, ((1, 0),))
    holdout = basis("holdout_source", interface, ((1, 0),))
    readout = basis("readout", interface, ((0, 1),))
    seed = build_calibration_seed(
        calibration_protocol_id="calibration.synthetic.v1",
        interface=interface,
        state_shape=(2,) + tuple(spatial_shape),
        dt=0.25,
        target_blind_parameters=(("mass", 1.0),),
        source_basis=source,
        holdout_source_basis=holdout,
        readout_basis=readout,
        boundary_manifest_id="periodic-v1",
        operator_payload=quarter_turn_operator(interface),
    )
    observation = measure_calibration_holdout(seed)
    target = freeze_synthetic_target(seed, observation, "target.synthetic.v1")
    return seed, observation, target


def trace_for(
    operator_payload,
    target,
    conditioned=(),
    *,
    conditioned_uses_target_production=True,
):
    conditioned = frozenset(conditioned)
    nodes = []
    specs = []
    for index, operator in enumerate(operator_payload):
        root = f"prov.{index}"
        is_conditioned = operator.mechanism_id in conditioned
        nodes.append(
            ProvenanceNode(
                provenance_id=root,
                operation=(
                    ProvenanceOperation.TARGET_SPEC_READ
                    if is_conditioned
                    else ProvenanceOperation.GRAMMAR_PRIMITIVE
                ),
                depends_on=(),
                target_refs=(
                    ("target:synthetic",) if is_conditioned else ()
                ),
                objective_tags=(),
                search_run_id=None,
                source_sha=SHA_A,
            )
        )
        value = complex(*operator.coefficient_wire)
        expression = sp.Integer(int(value.real))
        if value.imag:
            expression += sp.I * sp.Integer(int(value.imag))
        zero = (0,) * len(operator.offset)
        specs.append(
            PrimitiveSpec(
                mechanism_id=operator.mechanism_id,
                production_id=(
                    "target_operator"
                    if is_conditioned and conditioned_uses_target_production
                    else operator.production_id
                ),
                depends_on=(),
                support_offsets=tuple(sorted({zero, operator.offset})),
                state_channels=tuple(
                    sorted(
                        {
                            operator.source_channel,
                            operator.destination_channel,
                        }
                    )
                ),
                coefficient_expression=expression,
                coefficient_variable_order=(),
                symbolic_origin_tags=(),
                neutral_ablation="neutral-identity-v1",
                design_objective_tags=(),
                search_run_id=None,
                source_sha=SHA_A,
                design_provenance=root,
            )
        )
    return build_construction_trace(
        target_spec_id=target.target_spec_id,
        provenance_nodes=tuple(nodes),
        primitive_specs=tuple(specs),
    )


def actual_factory(conditioned=()):
    seed, observation, target = seed_target()
    conditioned_set = frozenset(conditioned)
    operator_payload = tuple(
        dataclasses.replace(
            item,
            production_id=(
                "target_operator"
                if item.mechanism_id in conditioned_set
                else item.production_id
            ),
        )
        for item in seed.runtime_operator_payload
    )
    trace = trace_for(
        operator_payload,
        target,
        conditioned=conditioned,
    )
    verified = build_factory_from_trace(
        trace,
        target,
        factory_id="factory.test.v1",
        interface=seed.interface,
        state_shape=seed.state_shape,
        dt=seed.dt,
        target_blind_parameters=seed.target_blind_parameters,
        layer_slot_ids=tuple(
            item.layer_slot_id for item in seed.runtime_operator_payload
        ),
        operator_payload=operator_payload,
        source_manifest_id=seed.source_basis.manifest_id,
        readout_basis=seed.readout_basis,
        boundary_manifest_id=seed.boundary_manifest_id,
    )
    return seed, observation, target, trace, verified


class FrozenWireTests(unittest.TestCase):
    def test_basis_and_tensor_are_self_hashed_deep_immutable_and_fresh(self):
        iface = interface_for(("x", "y"))
        source = basis("source", iface, ((1 + 2j, 0),))
        verify_basis_manifest(source)
        self.assertEqual(
            source.manifest_id,
            canonical_sha(basis_manifest_payload(source)),
        )
        a = basis_manifest_array(source)
        b = basis_manifest_array(source)
        self.assertEqual(a.dtype, np.complex128)
        self.assertFalse(np.shares_memory(a, b))
        a[0, 0] = 99
        self.assertEqual(b[0, 0], 1 + 2j)

        tensor = freeze_complex_tensor(np.arange(6).reshape(2, 3))
        verify_frozen_tensor(tensor)
        self.assertEqual(
            tensor.tensor_sha,
            canonical_sha(frozen_tensor_payload(tensor)),
        )
        x = frozen_tensor_array(tensor)
        y = frozen_tensor_array(tensor)
        self.assertFalse(np.shares_memory(x, y))
        x.flat[0] = 999
        self.assertEqual(y.flat[0], 0)

    def test_wire_validation_rejects_nonfinite_wrong_hash_and_empty_basis(self):
        iface = interface_for(("x", "y"))
        with self.assertRaisesRegex(ValueError, "non-empty"):
            build_basis_manifest(
                role="source",
                state_schema_id=iface.state_schema_id,
                channel_order=iface.channel_order,
                vectors=np.empty((0, 2), dtype=np.complex128),
            )
        with self.assertRaisesRegex(ValueError, "finite"):
            freeze_complex_tensor(np.asarray([np.inf + 0j]))
        good = basis("source", iface, ((1, 0),))
        with self.assertRaisesRegex(ValueError, "manifest_id"):
            verify_basis_manifest(dataclasses.replace(good, manifest_id="0" * 64))


class CalibrationAndFactoryTests(unittest.TestCase):
    @staticmethod
    def _resigned_factory_with_primitive(
        issued,
        primitive_index,
        **primitive_updates,
    ):
        primitives = list(issued.factory.primitives)
        primitives[primitive_index] = dataclasses.replace(
            primitives[primitive_index],
            **primitive_updates,
        )
        primitive_tuple = tuple(primitives)
        replacement = dataclasses.replace(
            issued.factory,
            primitives=primitive_tuple,
            runtime_operator_sha=runtime_operator_sha(primitive_tuple),
            factory_sha="0" * 64,
        )
        return dataclasses.replace(
            replacement,
            factory_sha=factory_sha(replacement),
        )

    def test_calibration_is_two_stage_self_hashed_and_measures_quarter_turn(self):
        seed, observation, target = seed_target()
        self.assertEqual(seed.seed_sha, canonical_sha(calibration_seed_payload(seed)))
        self.assertEqual(
            observation.observation_sha,
            canonical_sha(calibration_observation_payload(observation)),
        )
        self.assertEqual(
            target.target_spec_sha,
            canonical_sha(synthetic_target_payload(target)),
        )
        verify_synthetic_target(target)
        response = frozen_tensor_array(observation.response_tensor)
        self.assertEqual(response.shape, (1, 1, 9))
        self.assertAlmostEqual(response[0, 0, 0], 1.0)
        self.assertEqual(np.count_nonzero(response), 1)
        self.assertEqual(seed.runtime_operator_sha, runtime_operator_sha(
            seed.runtime_operator_payload
        ))

    def test_actual_factory_is_opaque_bound_and_executes_periodic_shear(self):
        seed, _, target, trace, verified = actual_factory()
        self.assertIsInstance(verified, VerifiedFactory)
        self.assertEqual(verified.role, "actual")
        self.assertEqual(
            verified.factory.factory_sha,
            factory_sha(verified.factory),
        )
        self.assertEqual(
            factory_payload(verified.factory)["run_length"],
            1,
        )
        self.assertEqual(
            verified.factory.runtime_operator_sha,
            seed.runtime_operator_sha,
        )
        verify_factory(verified.factory, trace, target)
        state = np.zeros(seed.state_shape, dtype=np.complex128)
        state[0, 2] = 3
        result = apply_factory_step(verified, state)
        self.assertEqual(result.dtype, np.complex128)
        np.testing.assert_array_equal(state[0], result[1])
        self.assertEqual(result[0, 2], 0)
        self.assertEqual(result[1, 2], 3)
        with self.assertRaises(TypeError):
            apply_factory_step(verified.factory, state)  # type: ignore[arg-type]

    def test_factory_issuer_normalizes_bad_top_level_and_incomplete_records(self):
        _, _, target, trace, issued = actual_factory()
        for factory_value, trace_value, target_value in (
            (None, trace, target),
            (issued.factory, None, target),
            (issued.factory, trace, None),
        ):
            with self.subTest(
                factory=type(factory_value).__name__,
                trace=type(trace_value).__name__,
                target=type(target_value).__name__,
            ):
                with self.assertRaises(TypeError):
                    verify_factory(  # type: ignore[arg-type]
                        factory_value,
                        trace_value,
                        target_value,
                    )

        for factory_value, trace_value, target_value in (
            (object.__new__(type(issued.factory)), trace, target),
            (issued.factory, object.__new__(type(trace)), target),
            (issued.factory, trace, object.__new__(type(target))),
        ):
            with self.subTest(
                incomplete=(
                    type(factory_value).__name__,
                    type(trace_value).__name__,
                    type(target_value).__name__,
                )
            ):
                with self.assertRaises(ValueError):
                    verify_factory(factory_value, trace_value, target_value)

    def test_verified_factory_wrapper_is_immutable_after_issuance(self):
        _, _, _, _, verified = actual_factory()
        with self.assertRaises(AttributeError):
            verified._VerifiedFactory__factory = verified.factory  # type: ignore[attr-defined]
        tampered = dataclasses.replace(
            verified.factory,
            dt=verified.factory.dt * 2.0,
            factory_sha="0" * 64,
        )
        tampered = dataclasses.replace(
            tampered,
            factory_sha=factory_sha(tampered),
        )
        object.__setattr__(
            verified,
            "_VerifiedFactory__factory",
            tampered,
        )
        with self.assertRaisesRegex(ValueError, "seal|registry|identity"):
            apply_factory_step(
                verified,
                np.zeros(tampered.state_shape, dtype=np.complex128),
            )

    def test_verified_factory_authority_has_no_raw_module_capability(self):
        from rulespace_v3 import factory as factory_module

        self.assertFalse(
            hasattr(factory_module, "_register_verified_factory_authority")
        )
        self.assertFalse(
            hasattr(factory_module, "_lookup_verified_factory_authority")
        )

    def test_exported_authority_callables_do_not_capture_raw_mutable_state(self):
        from rulespace_v3 import factory as factory_module

        lock_type = type(threading.RLock())
        for entrypoint in (
            factory_module._issue_verified_factory_wrapper,
            factory_module._reverify_verified_factory,
        ):
            with self.subTest(entrypoint=entrypoint.__name__):
                cells = tuple(
                    cell.cell_contents
                    for cell in (entrypoint.__closure__ or ())
                )
                self.assertTrue(cells)
                self.assertFalse(
                    any(isinstance(value, dict) for value in cells)
                )
                self.assertFalse(
                    any(isinstance(value, lock_type) for value in cells)
                )
                for value in cells:
                    self.assertFalse(hasattr(value, "get"))
                    self.assertFalse(hasattr(value, "set"))
                    self.assertFalse(hasattr(value, "enumerate"))

    def test_injected_authority_payload_is_fully_reverified_fail_closed(self):
        from rulespace_v3 import factory as factory_module

        _, _, _, _, issued = actual_factory()
        replacement = self._resigned_factory_with_primitive(
            issued,
            1,
            coefficient_wire=(2.0, 0.0),
        )

        pending = [factory_module._reverify_verified_factory]
        seen = set()
        registry = None
        while pending:
            function = pending.pop()
            if id(function) in seen:
                continue
            seen.add(id(function))
            for cell in function.__closure__ or ():
                value = cell.cell_contents
                if isinstance(value, dict) and id(issued) in value:
                    registry = value
                    pending.clear()
                    break
                if inspect.isfunction(value):
                    pending.append(value)
        self.assertIsNotNone(registry)
        assert registry is not None
        reference, authority = registry[id(issued)]
        trace, target = issued._bound_records()
        replacement_seal = factory_module._verified_factory_seal(
            replacement,
            trace,
            target,
        )
        registry[id(issued)] = (
            reference,
            dataclasses.replace(
                authority,
                factory=replacement,
                fingerprint=replacement_seal,
            ),
        )
        object.__setattr__(
            issued,
            "_VerifiedFactory__factory",
            replacement,
        )
        object.__setattr__(
            issued,
            "_VerifiedFactory__seal",
            replacement_seal,
        )
        with self.assertRaisesRegex(ValueError, "coefficient"):
            apply_factory_step(
                issued,
                np.zeros(replacement.state_shape, dtype=np.complex128),
            )

    def test_verified_factory_rejects_object_new_slot_copy(self):
        _, _, _, _, issued = actual_factory()
        forged = object.__new__(VerifiedFactory)
        for slot in ("factory", "trace", "target", "token", "seal"):
            object.__setattr__(
                forged,
                f"_VerifiedFactory__{slot}",
                object.__getattribute__(
                    issued,
                    f"_VerifiedFactory__{slot}",
                ),
            )
        with self.assertRaisesRegex(ValueError, "registry|identity"):
            apply_factory_step(
                forged,
                np.zeros(issued.factory.state_shape, dtype=np.complex128),
            )

    def test_verified_factory_rejects_hostile_subclass_without_hash_or_eq(self):
        _, _, _, _, issued = actual_factory()

        class HostileVerifiedFactory(VerifiedFactory):
            __slots__ = ()

            def __hash__(self):
                raise AssertionError("authority lookup called caller __hash__")

            def __eq__(self, other):
                del other
                raise AssertionError("authority lookup called caller __eq__")

        forged = object.__new__(HostileVerifiedFactory)
        for slot in ("factory", "trace", "target", "token", "seal"):
            object.__setattr__(
                forged,
                f"_VerifiedFactory__{slot}",
                object.__getattribute__(
                    issued,
                    f"_VerifiedFactory__{slot}",
                ),
            )
        with self.assertRaisesRegex(TypeError, "module-issued"):
            apply_factory_step(
                forged,
                np.zeros(issued.factory.state_shape, dtype=np.complex128),
            )

    def test_verified_factory_rejects_complete_slot_transplant_between_identities(self):
        _, _, _, _, actual = actual_factory(conditioned=("m0",))
        construction = matched_ablation(actual)
        assert construction.pair is not None
        matched = construction.pair.ablated
        for slot in ("factory", "trace", "target", "token", "seal"):
            object.__setattr__(
                actual,
                f"_VerifiedFactory__{slot}",
                object.__getattribute__(
                    matched,
                    f"_VerifiedFactory__{slot}",
                ),
            )
        with self.assertRaisesRegex(ValueError, "registry|identity"):
            apply_factory_step(
                actual,
                np.zeros(
                    matched.factory.state_shape,
                    dtype=np.complex128,
                ),
            )

    def test_verified_factory_registry_gc_and_stale_callback_are_id_safe(self):
        _, _, target, trace, issued = actual_factory()
        doomed = verify_factory(issued.factory, trace, target)
        doomed_id = id(doomed)
        registry_refs = tuple(
            ref
            for ref in weakref.getweakrefs(doomed)
            if ref.__callback__ is not None
        )
        self.assertEqual(len(registry_refs), 1)
        stale_ref = registry_refs[0]
        stale_callback = stale_ref.__callback__
        self.assertIsNotNone(stale_callback)
        del doomed
        gc.collect()
        self.assertIsNone(stale_ref())

        replacement = verify_factory(issued.factory, trace, target)
        assert stale_callback is not None
        # Deterministically model allocator id reuse: a delayed callback now
        # carries the replacement's numeric id but its own stale weakref.
        if doomed_id != id(replacement):
            setattr(stale_callback, "__defaults__", (id(replacement),))
        stale_callback(stale_ref)
        result = apply_factory_step(
            replacement,
            np.zeros(replacement.factory.state_shape, dtype=np.complex128),
        )
        self.assertEqual(result.shape, replacement.factory.state_shape)

    def test_verified_factory_issuance_and_runtime_are_thread_safe(self):
        _, _, target, trace, issued = actual_factory()
        state = np.zeros(issued.factory.state_shape, dtype=np.complex128)

        def issue_and_run(_index):
            wrapper = verify_factory(issued.factory, trace, target)
            return apply_factory_step(wrapper, state)

        with concurrent.futures.ThreadPoolExecutor(max_workers=8) as pool:
            results = tuple(pool.map(issue_and_run, range(64)))
        self.assertEqual(len(results), 64)
        for result in results:
            self.assertEqual(result.shape, issued.factory.state_shape)
            self.assertEqual(result.dtype, np.dtype(np.complex128))

    def test_executor_consumes_the_factory_verified_at_return_boundary(self):
        from rulespace_v3 import factory as factory_module

        _, _, _, _, issued = actual_factory()
        replacement = self._resigned_factory_with_primitive(
            issued,
            1,
            coefficient_wire=(2.0, 0.0),
        )
        state = np.zeros(issued.factory.state_shape, dtype=np.complex128)
        state[0, 2] = 3.0
        expected = apply_factory_step(issued, state)
        original_reverify = factory_module._reverify_verified_factory

        def reverify_then_swap(wrapper):
            verified = original_reverify(wrapper)
            object.__setattr__(
                wrapper,
                "_VerifiedFactory__factory",
                replacement,
            )
            return verified

        with mock.patch.object(
            factory_module,
            "_reverify_verified_factory",
            side_effect=reverify_then_swap,
        ):
            observed = apply_factory_step(issued, state)
        np.testing.assert_array_equal(observed, expected)

    def test_support_consumes_the_factory_verified_at_return_boundary(self):
        from rulespace_v3 import factory as factory_module

        _, _, _, _, issued = actual_factory()
        replacement = self._resigned_factory_with_primitive(
            issued,
            0,
            offset=(1,),
            support_offsets=((0,), (1,)),
        )
        expected = factory_support_offsets(issued, 1)
        original_reverify = factory_module._reverify_verified_factory

        def reverify_then_swap(wrapper):
            verified = original_reverify(wrapper)
            object.__setattr__(
                wrapper,
                "_VerifiedFactory__factory",
                replacement,
            )
            return verified

        with mock.patch.object(
            factory_module,
            "_reverify_verified_factory",
            side_effect=reverify_then_swap,
        ):
            observed = factory_support_offsets(issued, 1)
        self.assertEqual(observed, expected)

    def test_executor_never_runs_slot_replacement_under_concurrent_pressure(self):
        from rulespace_v3 import factory as factory_module

        _, _, _, _, issued = actual_factory()
        original = issued.factory
        replacement = self._resigned_factory_with_primitive(
            issued,
            1,
            coefficient_wire=(2.0, 0.0),
        )
        state = np.zeros(original.state_shape, dtype=np.complex128)
        state[0, 2] = 3.0
        expected = apply_factory_step(issued, state)
        stop = threading.Event()
        swap_requested = threading.Event()
        swap_finished = threading.Event()
        real_seal = factory_module._verified_factory_seal

        def swap_slots():
            while not stop.is_set():
                if not swap_requested.wait(timeout=5.0):
                    continue
                swap_requested.clear()
                if stop.is_set():
                    return
                object.__setattr__(
                    issued,
                    "_VerifiedFactory__factory",
                    replacement,
                )
                swap_finished.set()

        def seal_then_request_concurrent_swap(*args):
            fingerprint = real_seal(*args)
            swap_requested.set()
            if not swap_finished.wait(timeout=5.0):
                raise AssertionError("concurrent slot swap did not complete")
            swap_finished.clear()
            return fingerprint

        thread = threading.Thread(target=swap_slots)
        thread.start()
        try:
            with mock.patch.object(
                factory_module,
                "_verified_factory_seal",
                side_effect=seal_then_request_concurrent_swap,
            ):
                for _ in range(64):
                    object.__setattr__(
                        issued,
                        "_VerifiedFactory__factory",
                        original,
                    )
                    observed = apply_factory_step(issued, state)
                    np.testing.assert_array_equal(observed, expected)
        finally:
            stop.set()
            swap_requested.set()
            thread.join(timeout=5.0)
            object.__setattr__(
                issued,
                "_VerifiedFactory__factory",
                original,
            )
        self.assertFalse(thread.is_alive())

    def test_calibration_seed_rejects_every_signed_zero_shear(self):
        seed, _, _ = seed_target()
        for coefficient_wire in (
            (0.0, 0.0),
            (0.0, -0.0),
            (-0.0, 0.0),
            (-0.0, -0.0),
        ):
            with self.subTest(coefficient_wire=coefficient_wire):
                operators = (
                    dataclasses.replace(
                        seed.runtime_operator_payload[0],
                        coefficient_wire=coefficient_wire,
                    ),
                ) + seed.runtime_operator_payload[1:]
                with self.assertRaisesRegex(ValueError, "non-zero"):
                    build_calibration_seed(
                        calibration_protocol_id=seed.calibration_protocol_id,
                        interface=seed.interface,
                        state_shape=seed.state_shape,
                        dt=seed.dt,
                        target_blind_parameters=seed.target_blind_parameters,
                        source_basis=seed.source_basis,
                        holdout_source_basis=seed.holdout_source_basis,
                        readout_basis=seed.readout_basis,
                        boundary_manifest_id=seed.boundary_manifest_id,
                        operator_payload=operators,
                    )

    def test_actual_zero_coefficient_cannot_encode_a_second_noop(self):
        seed, _, target = seed_target()
        zero_operator = (
            dataclasses.replace(
                seed.runtime_operator_payload[0],
                coefficient_wire=(0.0, -0.0),
            ),
        ) + seed.runtime_operator_payload[1:]
        trace = trace_for(zero_operator, target)
        with self.assertRaisesRegex(ValueError, "non-zero"):
            build_factory_from_trace(
                trace,
                target,
                factory_id="factory.zero-shear.v1",
                interface=seed.interface,
                state_shape=seed.state_shape,
                dt=seed.dt,
                target_blind_parameters=seed.target_blind_parameters,
                layer_slot_ids=tuple(
                    item.layer_slot_id for item in zero_operator
                ),
                operator_payload=zero_operator,
                source_manifest_id=seed.source_basis.manifest_id,
                readout_basis=seed.readout_basis,
                boundary_manifest_id=seed.boundary_manifest_id,
            )

    def test_coefficient_wire_and_trace_binding_are_recomputed(self):
        _, _, target, trace, verified = actual_factory()
        bad_primitive = dataclasses.replace(
            verified.factory.primitives[0],
            coefficient_wire=(2.0, 0.0),
        )
        bad_factory = dataclasses.replace(
            verified.factory,
            primitives=(bad_primitive,) + verified.factory.primitives[1:],
        )
        bad_factory = dataclasses.replace(
            bad_factory,
            runtime_operator_sha=runtime_operator_sha(bad_factory.primitives),
        )
        bad_factory = dataclasses.replace(
            bad_factory,
            factory_sha=factory_sha(bad_factory),
        )
        with self.assertRaisesRegex(ValueError, "coefficient"):
            verify_factory(bad_factory, trace, target)

    def test_coefficient_wire_binding_distinguishes_signed_zero(self):
        seed, _, target = seed_target()
        operator_payload = (
            dataclasses.replace(
                seed.runtime_operator_payload[0],
                coefficient_wire=(1.0, -0.0),
            ),
        ) + seed.runtime_operator_payload[1:]
        trace = trace_for(operator_payload, target)
        with self.assertRaisesRegex(ValueError, "coefficient_wire"):
            build_factory_from_trace(
                trace,
                target,
                factory_id="factory.signed-zero.v1",
                interface=seed.interface,
                state_shape=seed.state_shape,
                dt=seed.dt,
                target_blind_parameters=seed.target_blind_parameters,
                layer_slot_ids=tuple(
                    item.layer_slot_id for item in operator_payload
                ),
                operator_payload=operator_payload,
                source_manifest_id=seed.source_basis.manifest_id,
                readout_basis=seed.readout_basis,
                boundary_manifest_id=seed.boundary_manifest_id,
            )

    def test_support_is_ordered_minkowski_and_needs_positive_macro_steps(self):
        _, _, _, _, verified = actual_factory()
        self.assertEqual(factory_support_offsets(verified, 1), ((0,),))
        self.assertEqual(factory_support_offsets(verified, 4), ((0,),))
        with self.assertRaises(ValueError):
            factory_support_offsets(verified, 0)

    def test_support_expansion_has_frozen_step_cardinality_and_allocation_limits(self):
        from rulespace_v3 import factory as factory_module

        _, _, _, _, verified = actual_factory()
        self.assertEqual(
            factory_support_offsets(
                verified,
                factory_module.FACTORY_SUPPORT_MAX_MACRO_STEPS,
            ),
            ((0,),),
        )
        with self.assertRaisesRegex(ValueError, "macro_steps limit"):
            factory_support_offsets(
                verified,
                factory_module.FACTORY_SUPPORT_MAX_MACRO_STEPS + 1,
            )

        class IterationBomb:
            def __len__(self):
                return 1001

            def __iter__(self):
                raise AssertionError("allocation gate must precede iteration")

        with self.assertRaisesRegex(ValueError, "allocation"):
            factory_module._minkowski(IterationBomb(), IterationBomb())

        left = tuple((index * 1000,) for index in range(1000))
        right = tuple((index,) for index in range(101))
        with self.assertRaisesRegex(ValueError, "cardinality"):
            factory_module._minkowski(left, right)

    def test_signed_periodic_offset_and_structural_support_follow_one_executor(self):
        iface = interface_for(("x.000", "y.000"))
        source = basis("source", iface, ((1, 0),))
        holdout = basis("holdout_source", iface, ((1, 0),))
        readout = basis("readout", iface, ((0, 1),))
        operator = (
            PrimitiveOperatorWire(
                mechanism_id="translated",
                production_id="local_canonical_shear",
                layer_slot_id="slot.translated",
                operation_id="local_canonical_shear",
                interface_id=iface.interface_id,
                source_channel="x.000",
                destination_channel="y.000",
                offset=(1,),
                coefficient_wire=(1.0, 0.0),
            ),
        )
        seed = build_calibration_seed(
            calibration_protocol_id="calibration.offset.v1",
            interface=iface,
            state_shape=(2, 9),
            dt=0.25,
            target_blind_parameters=(),
            source_basis=source,
            holdout_source_basis=holdout,
            readout_basis=readout,
            boundary_manifest_id="periodic-v1",
            operator_payload=operator,
        )
        observation = measure_calibration_holdout(seed)
        target = freeze_synthetic_target(
            seed,
            observation,
            "target.offset.v1",
        )
        trace = trace_for(operator, target)
        verified = build_factory_from_trace(
            trace,
            target,
            factory_id="factory.offset.v1",
            interface=iface,
            state_shape=seed.state_shape,
            dt=seed.dt,
            target_blind_parameters=(),
            layer_slot_ids=("slot.translated",),
            operator_payload=operator,
            source_manifest_id=source.manifest_id,
            readout_basis=readout,
            boundary_manifest_id="periodic-v1",
        )
        state = np.zeros((2, 9), dtype=np.complex128)
        state[0, 2] = 1
        result = apply_factory_step(verified, state)
        self.assertEqual(result[1, 1], 1)
        self.assertEqual(np.count_nonzero(result[1]), 1)
        self.assertEqual(factory_support_offsets(verified, 1), ((0,), (1,)))
        self.assertEqual(
            factory_support_offsets(verified, 2),
            ((0,), (1,), (2,)),
        )


class MatchedAblationTests(unittest.TestCase):
    def report(self, factory_sha_value, **updates):
        values = dict(
            report_schema_version="v3m0.ablation-dynamics-report.v1",
            factory_sha=factory_sha_value,
            state_schema_matches=True,
            reversible=True,
            stable=True,
            certificate_sha="e" * 64,
            report_sha="0" * 64,
        )
        values.update(updates)
        report = AblationDynamicsReport(**values)
        return dataclasses.replace(
            report,
            report_sha=canonical_sha(dynamics_report_payload(report)),
        )

    def test_conditioned_slots_become_only_canonical_neutral(self):
        _, _, _, _, verified = actual_factory(conditioned=("m0", "m2"))
        outcome = matched_ablation(verified)
        self.assertTrue(outcome.status.defined)
        self.assertIsNotNone(outcome.pair)
        pair = verify_ablation_pair(outcome.pair)
        self.assertEqual(len(pair.manifest.replacements), 2)
        operations = tuple(
            primitive.operation_id
            for primitive in pair.ablated.factory.primitives
        )
        self.assertEqual(
            operations,
            ("neutral_identity", "local_canonical_shear", "neutral_identity"),
        )
        for index in (0, 2):
            primitive = pair.ablated.factory.primitives[index]
            self.assertEqual(primitive.offset, (0,))
            self.assertEqual(primitive.support_offsets, ((0,),))
            self.assertEqual(primitive.coefficient_wire, (0.0, 0.0))
            self.assertEqual(
                primitive.neutral_identity_id,
                "neutral-identity-v1",
            )
        self.assertEqual(
            pair.actual.factory.layer_slot_ids,
            pair.ablated.factory.layer_slot_ids,
        )

        tampered_manifest = dataclasses.replace(
            pair.manifest,
            replacements=(),
            manifest_sha="0" * 64,
        )
        tampered_manifest = dataclasses.replace(
            tampered_manifest,
            manifest_sha=canonical_sha(
                ablation_manifest_payload(tampered_manifest)
            ),
        )
        with self.assertRaisesRegex(ValueError, "replacements"):
            verify_ablation_pair(
                dataclasses.replace(pair, manifest=tampered_manifest)
            )

    def test_matched_ablation_consumes_one_view_and_reissues_pair_actual(self):
        from rulespace_v3 import ablation as ablation_module

        _, _, _, _, caller = actual_factory(conditioned=("m0",))
        primitive_tuple = (
            caller.factory.primitives[0],
            dataclasses.replace(
                caller.factory.primitives[1],
                coefficient_wire=(2.0, 0.0),
            ),
            caller.factory.primitives[2],
        )
        replacement = dataclasses.replace(
            caller.factory,
            primitives=primitive_tuple,
            runtime_operator_sha=runtime_operator_sha(primitive_tuple),
            factory_sha="0" * 64,
        )
        replacement = dataclasses.replace(
            replacement,
            factory_sha=factory_sha(replacement),
        )
        original_reverify = ablation_module._reverify_verified_factory
        changed = False

        def reverify_then_change_caller(wrapper):
            nonlocal changed
            snapshot = original_reverify(wrapper)
            if wrapper is caller and not changed:
                changed = True
                object.__setattr__(
                    caller,
                    "_VerifiedFactory__factory",
                    replacement,
                )
            return snapshot

        with mock.patch.object(
            ablation_module,
            "_reverify_verified_factory",
            side_effect=reverify_then_change_caller,
        ):
            outcome = matched_ablation(caller)

        self.assertTrue(changed)
        self.assertTrue(outcome.status.defined)
        self.assertIsNotNone(outcome.pair)
        assert outcome.pair is not None
        self.assertIsNot(outcome.pair.actual, caller)
        self.assertEqual(
            outcome.pair.manifest.manifest_sha,
            canonical_sha(
                ablation_manifest_payload(outcome.pair.manifest)
            ),
        )
        self.assertIs(verify_ablation_pair(outcome.pair), outcome.pair)

        failed = matched_ablation(caller)
        self.assertFalse(failed.status.defined)
        first = qualify_ablation(failed, None)
        second = qualify_ablation(failed, None)
        self.assertEqual(first.qualification_sha, second.qualification_sha)

    def test_unclassified_trace_fails_without_pair(self):
        seed, _, target = seed_target()
        operator = seed.runtime_operator_payload
        node = ProvenanceNode(
            provenance_id="opaque",
            operation=ProvenanceOperation.OPAQUE_LITERAL,
            depends_on=(),
            target_refs=(),
            objective_tags=(),
            search_run_id=None,
            source_sha=SHA_A,
        )
        specifications = []
        for index, item in enumerate(operator):
            specifications.append(
                PrimitiveSpec(
                    mechanism_id=item.mechanism_id,
                    production_id=item.production_id,
                    depends_on=(),
                    support_offsets=((0,),),
                    state_channels=tuple(
                        sorted((item.source_channel, item.destination_channel))
                    ),
                    coefficient_expression=sp.Integer(
                        int(item.coefficient_wire[0])
                    ),
                    coefficient_variable_order=(),
                    symbolic_origin_tags=(),
                    neutral_ablation="neutral-identity-v1",
                    design_objective_tags=(),
                    search_run_id=None,
                    source_sha=SHA_A,
                    design_provenance="opaque",
                )
            )
        trace = build_construction_trace(
            target_spec_id=target.target_spec_id,
            provenance_nodes=(node,),
            primitive_specs=tuple(specifications),
        )
        factory = build_factory_from_trace(
            trace,
            target,
            factory_id="opaque.factory",
            interface=seed.interface,
            state_shape=seed.state_shape,
            dt=seed.dt,
            target_blind_parameters=seed.target_blind_parameters,
            layer_slot_ids=tuple(x.layer_slot_id for x in operator),
            operator_payload=operator,
            source_manifest_id=seed.source_basis.manifest_id,
            readout_basis=seed.readout_basis,
            boundary_manifest_id="periodic-v1",
        )
        outcome = matched_ablation(factory)
        self.assertEqual(
            outcome.status,
            BlockStatus(False, UndefinedReason.TRACE_UNCLASSIFIED),
        )
        self.assertIsNone(outcome.pair)

    def test_qualification_is_fail_closed_until_task10_certificate_issuer(self):
        from rulespace_v3 import ablation as ablation_module

        _, _, _, _, verified = actual_factory(conditioned=("m0",))
        outcome = matched_ablation(verified)
        assert outcome.pair is not None
        sha = outcome.pair.ablated.factory.factory_sha
        reports = (
            self.report(sha),
            self.report("b" * 64),
            self.report(
                sha,
                state_schema_matches=False,
                reversible=False,
                stable=False,
            ),
            self.report(sha, reversible=False, stable=False),
            self.report(sha, stable=False),
        )
        for report in reports:
            with self.subTest(report=report):
                with self.assertRaises(TypeError):
                    qualify_ablation(outcome, report)
        self.assertFalse(
            hasattr(ablation_module, "_DYNAMICS_AUTHORITY_CAPABILITY")
        )
        self.assertFalse(
            hasattr(ablation_module, "_issue_verified_dynamics_report")
        )
        forged_authority = object.__new__(VerifiedDynamicsReport)
        with self.assertRaisesRegex(ValueError, "Task 10|unavailable"):
            verify_verified_dynamics_report(forged_authority)
        with self.assertRaises((TypeError, ValueError)):
            qualify_ablation(outcome, forged_authority)
        with self.assertRaises(TypeError):
            QualifiedAblationOutcome(
                object(),
                outcome,
                BlockStatus(True, None),
                outcome.pair,
                None,
            )

        failed = AblationConstructionOutcome(
            BlockStatus(False, UndefinedReason.TRACE_UNCLASSIFIED),
            None,
        )
        propagated = qualify_ablation(failed, None)
        self.assertIsNone(propagated.pair)
        self.assertIsNone(propagated.dynamics_report)
        self.assertRegex(propagated.qualification_sha, r"[0-9a-f]{64}\Z")
        self.assertEqual(
            propagated.qualification_sha,
            qualify_ablation(failed, None).qualification_sha,
        )
        different_failure = AblationConstructionOutcome(
            BlockStatus(False, UndefinedReason.MANIFEST_MISMATCH),
            None,
        )
        self.assertNotEqual(
            propagated.qualification_sha,
            qualify_ablation(different_failure, None).qualification_sha,
        )
        qualification_sha = propagated.qualification_sha
        self.assertIs(verify_qualified_ablation(propagated), propagated)
        self.assertEqual(propagated.qualification_sha, qualification_sha)
        with self.assertRaises(TypeError):
            qualify_ablation(outcome, None)

    def test_qualified_outcome_rejects_object_new_and_private_tampering(self):
        failed = AblationConstructionOutcome(
            BlockStatus(False, UndefinedReason.TRACE_UNCLASSIFIED),
            None,
        )
        issued = qualify_ablation(failed, None)

        forged = object.__new__(QualifiedAblationOutcome)
        object.__setattr__(
            forged,
            "_QualifiedAblationOutcome__status",
            BlockStatus(True, None),
        )
        object.__setattr__(
            forged,
            "_QualifiedAblationOutcome__pair",
            None,
        )
        object.__setattr__(
            forged,
            "_QualifiedAblationOutcome__dynamics_report",
            None,
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_qualified_ablation(forged)

        sha_tampered = qualify_ablation(failed, None)
        object.__setattr__(
            sha_tampered,
            "_QualifiedAblationOutcome__seal",
            "f" * 64,
        )
        with self.assertRaisesRegex(ValueError, "seal"):
            verify_qualified_ablation(sha_tampered)

        object.__setattr__(
            issued,
            "_QualifiedAblationOutcome__status",
            BlockStatus(False, UndefinedReason.MANIFEST_MISMATCH),
        )
        with self.assertRaisesRegex(ValueError, "seal|status"):
            verify_qualified_ablation(issued)


class SyntheticControlTests(unittest.TestCase):
    @staticmethod
    def response_rank(factory, source_basis):
        state_shape = factory.factory.state_shape
        sources = basis_manifest_array(source_basis)
        readout = basis_manifest_array(factory.factory.readout_basis)
        matrix = np.zeros(
            (readout.shape[0], sources.shape[0]),
            dtype=np.complex128,
        )
        origin = (0,) * (len(state_shape) - 1)
        for column, source_vector in enumerate(sources):
            state = np.zeros(state_shape, dtype=np.complex128)
            state[(slice(None),) + origin] = source_vector
            result = apply_factory_step(factory, state)
            matrix[:, column] = readout.conj() @ result[(slice(None),) + origin]
        return int(np.linalg.matrix_rank(matrix))

    def test_full_zero_and_direct_sum_have_frozen_rank_triangle(self):
        seed, observation, target = seed_target()
        full = build_full_control(seed, observation, target)
        zero = build_zero_control(2, target, (9,), 0.25)
        direct = build_direct_sum_control(2, target, (9,), 0.25)

        for bundle, expected_id, actual_rank, ablated_rank in (
            (full, "full", 1, 1),
            (zero, "zero", 2, 0),
            (direct, "direct_sum", 4, 2),
        ):
            self.assertEqual(bundle.control_id, expected_id)
            self.assertEqual(bundle.expected_actual_rank, actual_rank)
            self.assertEqual(bundle.expected_ablated_rank, ablated_rank)
            self.assertEqual(
                self.response_rank(bundle.factory, bundle.source_basis),
                actual_rank,
            )
            outcome = matched_ablation(bundle.factory)
            self.assertTrue(outcome.status.defined)
            assert outcome.pair is not None
            if expected_id == "full":
                self.assertEqual(outcome.pair.manifest.replacements, ())
            self.assertEqual(
                self.response_rank(
                    outcome.pair.ablated,
                    bundle.source_basis,
                ),
                ablated_rank,
            )

    def test_control_entrypoints_reject_wrong_record_types_before_access(self):
        seed, observation, target = seed_target()
        for seed_value, observation_value, target_value in (
            (None, observation, target),
            (seed, None, target),
            (seed, observation, None),
        ):
            with self.subTest(
                seed=type(seed_value).__name__,
                observation=type(observation_value).__name__,
                target=type(target_value).__name__,
            ):
                with self.assertRaises(TypeError):
                    build_full_control(  # type: ignore[arg-type]
                        seed_value,
                        observation_value,
                        target_value,
                    )

    def test_invalid_control_target_fails_before_canonical_basis_allocation(self):
        from rulespace_v3 import controls as controls_module

        _, _, target = seed_target()
        invalid_target = dataclasses.replace(
            target,
            target_spec_sha="0" * 64,
        )
        with mock.patch.object(
            controls_module,
            "_canonical_basis",
            side_effect=AssertionError("basis allocation ran too early"),
        ):
            with self.assertRaisesRegex(ValueError, "target_spec_sha"):
                build_zero_control(1, invalid_target, (9,), 0.25)

    def test_full_cheap_canonical_checks_precede_holdout_measurement(self):
        from rulespace_v3 import controls as controls_module

        seed, observation, target = seed_target()
        invalid_interface = dataclasses.replace(
            seed.interface,
            channel_order=("bad.x", "bad.y"),
        )
        invalid_seed = dataclasses.replace(
            seed,
            interface=invalid_interface,
            seed_sha="0" * 64,
        )
        invalid_seed = dataclasses.replace(
            invalid_seed,
            seed_sha=canonical_sha(calibration_seed_payload(invalid_seed)),
        )
        with mock.patch.object(
            controls_module,
            "measure_calibration_holdout",
            side_effect=AssertionError("holdout measurement ran too early"),
        ):
            with self.assertRaisesRegex(ValueError, "channel_order"):
                build_full_control(invalid_seed, observation, target)

    def test_control_labels_do_not_enter_generic_executor_contracts(self):
        self.assertNotIn("control", inspect.signature(apply_factory_step).parameters)
        self.assertNotIn("control", inspect.signature(factory_support_offsets).parameters)
        executor_source = inspect.getsource(apply_factory_step)
        self.assertNotIn("control_id", executor_source)
        self.assertNotIn("startswith", executor_source)
        rank_source = inspect.getsource(self.response_rank)
        self.assertNotIn("startswith", rank_source)
        self.assertNotIn("control_id", rank_source)
        seed, _, _ = seed_target()
        for item in primitive_operator_payload(seed.runtime_operator_payload):
            self.assertFalse(any("control" in key for key in item))

    def test_full_rejects_noncanonical_source_and_non_quarter_turn_seed(self):
        seed, observation, target = seed_target()
        wrong_protocol_target = dataclasses.replace(
            target,
            calibration_protocol_id="calibration.synthetic.other.v1",
            target_spec_sha="0" * 64,
        )
        wrong_protocol_target = dataclasses.replace(
            wrong_protocol_target,
            target_spec_sha=canonical_sha(
                synthetic_target_payload(wrong_protocol_target)
            ),
        )
        with self.assertRaisesRegex(ValueError, "calibration_protocol_id"):
            build_full_control(seed, observation, wrong_protocol_target)

        wrong_source = build_basis_manifest(
            role="source",
            state_schema_id=seed.interface.state_schema_id,
            channel_order=seed.interface.channel_order,
            vectors=np.asarray(((0, 1),), dtype=np.complex128),
        )
        bad_basis_seed = build_calibration_seed(
            calibration_protocol_id=seed.calibration_protocol_id,
            interface=seed.interface,
            state_shape=seed.state_shape,
            dt=seed.dt,
            target_blind_parameters=seed.target_blind_parameters,
            source_basis=wrong_source,
            holdout_source_basis=seed.holdout_source_basis,
            readout_basis=seed.readout_basis,
            boundary_manifest_id=seed.boundary_manifest_id,
            operator_payload=seed.runtime_operator_payload,
        )
        bad_basis_observation = measure_calibration_holdout(bad_basis_seed)
        bad_basis_target = freeze_synthetic_target(
            bad_basis_seed,
            bad_basis_observation,
            "target.synthetic.noncanonical-basis.v1",
        )
        with self.assertRaisesRegex(ValueError, "canonical source"):
            build_full_control(
                bad_basis_seed,
                bad_basis_observation,
                bad_basis_target,
            )

        short_seed = build_calibration_seed(
            calibration_protocol_id=seed.calibration_protocol_id,
            interface=seed.interface,
            state_shape=seed.state_shape,
            dt=seed.dt,
            target_blind_parameters=seed.target_blind_parameters,
            source_basis=seed.source_basis,
            holdout_source_basis=seed.holdout_source_basis,
            readout_basis=seed.readout_basis,
            boundary_manifest_id=seed.boundary_manifest_id,
            operator_payload=seed.runtime_operator_payload[:1],
        )
        short_observation = measure_calibration_holdout(short_seed)
        short_target = freeze_synthetic_target(
            short_seed,
            short_observation,
            "target.synthetic.short-seed.v1",
        )
        with self.assertRaisesRegex(ValueError, "three-shear quarter-turn"):
            build_full_control(short_seed, short_observation, short_target)

    def test_full_factory_requires_entire_trace_to_be_target_blind(self):
        seed, _, target = seed_target()
        conditioned_trace = trace_for(
            seed.runtime_operator_payload,
            target,
            conditioned=("m0",),
            conditioned_uses_target_production=False,
        )
        with self.assertRaisesRegex(ValueError, "target-blind"):
            build_full_factory_from_seed(
                conditioned_trace,
                target,
                seed,
                factory_id="synthetic.local-linear.factory.v1",
                layer_slot_ids=tuple(
                    item.layer_slot_id
                    for item in seed.runtime_operator_payload
                ),
            )


if __name__ == "__main__":
    unittest.main()
