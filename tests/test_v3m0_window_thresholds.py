from __future__ import annotations

import copy
import dataclasses
import dis
import inspect
import math
import unittest
from unittest import mock

import numpy as np

from tests.test_v3m0_dynamics import _quarter_turn_controls

from rulespace_v3.controls import (
    build_direct_sum_control,
    build_full_control,
    build_zero_control,
)
from rulespace_v3.evidence import canonical_sha
from rulespace_v3.factory import (
    PrimitiveInterface,
    PrimitiveOperatorWire,
    build_basis_manifest,
    build_calibration_seed,
    freeze_synthetic_target,
    measure_calibration_holdout,
)
from rulespace_v3.registry import (
    CONTROL_ORDER,
    ClosedControlRegistry,
    VerifiedControlRegistry,
    build_closed_control_registry,
    verify_closed_control_registry,
)
from rulespace_v3.parent_freeze import issue_v3m0_parent_freeze
from rulespace_v3.thresholds import (
    BRIDGE_TOLERANCE,
    EPS_FP64,
    FEJER_WORK_MAX,
    GENERAL_EVIDENCE_BODY_BYTES_MAX,
    OVERLAP_MARGIN_MIN,
    PROJECTOR_T2T_MAX,
    RAW_GAP_MIN,
    SHELL_LOOP_RESIDUAL_MAX,
    SHELL_PARTICIPATION_MIN,
    SHELL_PROJECTOR_ENTRIES_MAX,
    SHELL_PROJECTOR_RESIDUAL_MAX,
    SIGNAL_NOISE_RATIO_MIN,
    SOURCE_BRIDGE_WORK_MAX,
    T_CANDIDATES,
    compute_signal_threshold_values,
    phase_grid_step,
    phase_separation_min,
    preflight_fejer_work,
    preflight_general_evidence_body,
    preflight_shell_projector_entries,
    preflight_source_bridge_work,
    verify_window_comparison_gates,
    verify_window_protocol_thresholds,
)
from rulespace_v3.window import (
    WINDOW_CALIBRATION_PROTOCOL_SCHEMA_VERSION,
    ControlWindowProtocolEntry,
    VerifiedWindowCalibrationProtocol,
    WindowCalibrationProtocol,
    build_control_window_protocol_entries,
    build_window_calibration_protocol,
    control_window_protocol_entry_payload,
    verify_window_calibration_protocol,
    window_calibration_protocol_payload,
)


GENERAL_EVIDENCE_TEXT_BYTES_MAX = 16_384
GENERAL_EVIDENCE_SPATIAL_NDIM_MAX = 64


def _window_controls(
    spatial_shape: tuple[int, ...] = (8,),
):
    interface = PrimitiveInterface(
        interface_id="interface.synthetic.local-linear.v1",
        state_schema_id="state.synthetic.local-linear.v1",
        spatial_ndim=len(spatial_shape),
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
            offset=(0,) * len(spatial_shape),
            coefficient_wire=(coefficients[layer], 0.0),
        )
        for layer in range(3)
    )
    seed = build_calibration_seed(
        calibration_protocol_id="calibration.synthetic.v1",
        interface=interface,
        state_shape=(2,) + spatial_shape,
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
        build_zero_control(1, target, spatial_shape, 0.25),
        build_direct_sum_control(1, target, spatial_shape, 0.25),
    )


class FrozenThresholdTests(unittest.TestCase):
    def test_closed_orders_formulas_and_hard_constants(self):
        self.assertEqual(
            T_CANDIDATES,
            (256, 512, 1024, 2048, 4096, 8192),
        )
        for order in T_CANDIDATES + (16384,):
            with self.subTest(order=order):
                self.assertEqual(
                    phase_grid_step(order),
                    2.0 * math.pi / (16 * order),
                )
                self.assertEqual(
                    phase_separation_min(order),
                    8.0 * math.pi / order,
                )
        self.assertEqual(SHELL_PARTICIPATION_MIN, 0.25)
        self.assertEqual(OVERLAP_MARGIN_MIN, 0.2)
        self.assertEqual(SHELL_PROJECTOR_RESIDUAL_MAX, 1.0e-12)
        self.assertEqual(SHELL_LOOP_RESIDUAL_MAX, 1.0e-10)
        self.assertEqual(PROJECTOR_T2T_MAX, 1.0e-10)
        self.assertEqual(SIGNAL_NOISE_RATIO_MIN, 1.0e3)
        self.assertEqual(RAW_GAP_MIN, 1.0e3)
        self.assertEqual(BRIDGE_TOLERANCE, 1.0e-12)
        self.assertEqual(EPS_FP64, 2.0**-52)

    def test_phase_formulas_only_accept_preregistered_candidate_or_2t_orders(self):
        for invalid in (True, 255, 32768, 256.0, "256"):
            with self.subTest(invalid=invalid):
                with self.assertRaises((TypeError, ValueError)):
                    phase_grid_step(invalid)  # type: ignore[arg-type]
                with self.assertRaises((TypeError, ValueError)):
                    phase_separation_min(invalid)  # type: ignore[arg-type]

    def test_window_comparison_gate_uses_frozen_inclusive_boundaries(self):
        order = 256
        self.assertTrue(
            verify_window_comparison_gates(
                order=order,
                phase_separation=phase_separation_min(order),
                overlap_margin=OVERLAP_MARGIN_MIN,
                projector_t2t_distance=PROJECTOR_T2T_MAX,
            )
        )
        self.assertFalse(
            verify_window_comparison_gates(
                order=order,
                phase_separation=math.nextafter(
                    phase_separation_min(order),
                    -math.inf,
                ),
                overlap_margin=OVERLAP_MARGIN_MIN,
                projector_t2t_distance=PROJECTOR_T2T_MAX,
            )
        )
        self.assertFalse(
            verify_window_comparison_gates(
                order=order,
                phase_separation=phase_separation_min(order),
                overlap_margin=math.nextafter(
                    OVERLAP_MARGIN_MIN,
                    -math.inf,
                ),
                projector_t2t_distance=PROJECTOR_T2T_MAX,
            )
        )
        self.assertFalse(
            verify_window_comparison_gates(
                order=order,
                phase_separation=phase_separation_min(order),
                overlap_margin=OVERLAP_MARGIN_MIN,
                projector_t2t_distance=math.nextafter(
                    PROJECTOR_T2T_MAX,
                    math.inf,
                ),
            )
        )

    def test_signal_line_is_mechanical_log_midpoint_with_fp64_floor(self):
        exact_null = compute_signal_threshold_values(
            scale_ref=4.0,
            null_max=None,
            bridge_operator_error_max=0.0,
            signal_min=1.0,
            raw_relative_gap=2.0e3,
        )
        self.assertEqual(exact_null.noise_ref, EPS_FP64 * 4.0)
        self.assertEqual(
            exact_null.tau_sig,
            math.sqrt(exact_null.noise_ref),
        )
        self.assertEqual(
            exact_null.signal_noise_ratio,
            1.0 / exact_null.noise_ref,
        )
        self.assertTrue(exact_null.absolute_signal_gate_passed)
        self.assertTrue(exact_null.relative_gap_gate_passed)

    def test_signal_line_extreme_fp64_domain_is_finite_or_fails_closed(self):
        largest = math.nextafter(math.inf, 0.0)
        valid_cases = (
            (1.0e-307, 1.0e-307),
            (1.0e308, 1.0e308),
            (largest, largest),
        )
        for scale, signal in valid_cases:
            with self.subTest(scale=scale, signal=signal):
                observed = compute_signal_threshold_values(
                    scale_ref=scale,
                    null_max=None,
                    bridge_operator_error_max=0.0,
                    signal_min=signal,
                    raw_relative_gap=1_000.0,
                )
                for value in (
                    observed.scale_ref,
                    observed.noise_ref,
                    observed.signal_min,
                    observed.tau_sig,
                    observed.signal_noise_ratio,
                ):
                    self.assertTrue(math.isfinite(value))
                    self.assertGreater(value, 0.0)
                self.assertGreaterEqual(
                    observed.tau_sig,
                    min(observed.noise_ref, observed.signal_min),
                )
                self.assertLessEqual(
                    observed.tau_sig,
                    max(observed.noise_ref, observed.signal_min),
                )

        tiny = math.nextafter(0.0, 1.0)
        invalid_cases = (
            (tiny, None, 0.0, tiny),
            (1.0e-308, None, 0.0, 1.0e-308),
            (tiny, None, tiny, largest),
            (largest, largest, largest, tiny),
        )
        for scale, null, bridge, signal in invalid_cases:
            with self.subTest(
                scale=scale,
                null=null,
                bridge=bridge,
                signal=signal,
            ):
                with self.assertRaisesRegex(
                    ValueError,
                    "finite|positive|representable|range",
                ):
                    compute_signal_threshold_values(
                        scale_ref=scale,
                        null_max=null,
                        bridge_operator_error_max=bridge,
                        signal_min=signal,
                        raw_relative_gap=1_000.0,
                    )

        noisy = compute_signal_threshold_values(
            scale_ref=2.0,
            null_max=0.02,
            bridge_operator_error_max=0.01,
            signal_min=1.0,
            raw_relative_gap=999.0,
        )
        self.assertEqual(noisy.noise_ref, 0.02)
        self.assertEqual(noisy.tau_sig, math.sqrt(0.02))
        self.assertFalse(noisy.absolute_signal_gate_passed)
        self.assertFalse(noisy.relative_gap_gate_passed)

    def test_resource_caps_are_checked_by_the_frozen_work_formulas(self):
        self.assertEqual(
            preflight_source_bridge_work(
                n_k=64,
                n_trial=2,
                steps=(1, 2, 256),
            ),
            64 * 2 * 256,
        )
        with self.assertRaisesRegex(ValueError, "source bridge work"):
            preflight_source_bridge_work(
                n_k=64,
                n_trial=2,
                steps=(1, 2, 257),
            )
        self.assertEqual(
            preflight_shell_projector_entries(
                n_k=1,
                n_state=4096,
            ),
            SHELL_PROJECTOR_ENTRIES_MAX,
        )
        with self.assertRaisesRegex(ValueError, "projector entries"):
            preflight_shell_projector_entries(
                n_k=2,
                n_state=4096,
            )
        self.assertEqual(
            preflight_fejer_work(
                n_k=1,
                n_state=1,
                order=256,
            ),
            257,
        )
        with self.assertRaisesRegex(ValueError, "Fejer work"):
            preflight_fejer_work(
                n_k=FEJER_WORK_MAX,
                n_state=2,
                order=256,
            )
        self.assertEqual(
            preflight_general_evidence_body(
                GENERAL_EVIDENCE_BODY_BYTES_MAX,
            ),
            GENERAL_EVIDENCE_BODY_BYTES_MAX,
        )
        with self.assertRaisesRegex(ValueError, "evidence body"):
            preflight_general_evidence_body(
                GENERAL_EVIDENCE_BODY_BYTES_MAX + 1,
            )
        self.assertEqual(SOURCE_BRIDGE_WORK_MAX, 32_768)

    def test_task11_signal_module_does_not_publish_downstream_thresholds(self):
        import rulespace_v3.thresholds as thresholds

        forbidden = {
            "TAU_SURV",
            "TAU_GEOM",
            "TAU_COVER",
            "SURVIVAL_THRESHOLD",
            "GEOMETRY_THRESHOLD",
            "COVERAGE_THRESHOLD",
        }
        self.assertTrue(forbidden.isdisjoint(vars(thresholds)))

    def test_frozen_threshold_arithmetic_ignores_module_global_monkeypatches(
        self,
    ):
        import rulespace_v3.thresholds as thresholds

        expected_grid = phase_grid_step(256)
        expected_separation = phase_separation_min(256)
        with (
            mock.patch.object(thresholds, "T_CANDIDATES", (1,)),
            mock.patch.object(thresholds, "FEJER_ORDERS", (1,)),
            mock.patch.object(thresholds, "OVERLAP_MARGIN_MIN", 0.0),
            mock.patch.object(thresholds, "PROJECTOR_T2T_MAX", 1.0),
            mock.patch.object(thresholds, "SIGNAL_NOISE_RATIO_MIN", 0.0),
            mock.patch.object(thresholds, "RAW_GAP_MIN", 0.0),
            mock.patch.object(thresholds, "EPS_FP64", 0.0),
            mock.patch.object(
                thresholds,
                "SOURCE_BRIDGE_WORK_MAX",
                10**30,
            ),
            mock.patch.object(
                thresholds,
                "_closed_order",
                return_value=1,
            ),
            mock.patch.object(
                thresholds,
                "_positive_int",
                side_effect=lambda value, field: int(value),
            ),
            mock.patch.object(
                thresholds,
                "_finite_nonnegative_float",
                side_effect=lambda value, field: float(value),
            ),
            mock.patch.object(
                thresholds,
                "_finite_positive_float",
                side_effect=lambda value, field: float(value),
            ),
            mock.patch.object(thresholds.math, "pi", 3.0),
        ):
            self.assertEqual(phase_grid_step(256), expected_grid)
            self.assertEqual(
                phase_separation_min(256),
                expected_separation,
            )
            self.assertFalse(
                verify_window_comparison_gates(
                    order=256,
                    phase_separation=expected_separation,
                    overlap_margin=0.0,
                    projector_t2t_distance=1.0,
                )
            )
            values = compute_signal_threshold_values(
                scale_ref=1.0,
                null_max=0.01,
                bridge_operator_error_max=0.0,
                signal_min=1.0,
                raw_relative_gap=999.0,
            )
            self.assertFalse(values.absolute_signal_gate_passed)
            self.assertFalse(values.relative_gap_gate_passed)
            with self.assertRaisesRegex(ValueError, "source bridge work"):
                preflight_source_bridge_work(
                    n_k=64,
                    n_trial=2,
                    steps=(1, 2, 257),
                )

    def test_frozen_builtin_arithmetic_cannot_be_rebound(self):
        import rulespace_v3.thresholds as thresholds

        expected = compute_signal_threshold_values(
            scale_ref=1.0,
            null_max=0.01,
            bridge_operator_error_max=0.02,
            signal_min=1.0,
            raw_relative_gap=1_000.0,
        )
        with mock.patch.object(
            thresholds,
            "max",
            create=True,
            return_value=0.0,
        ):
            observed = compute_signal_threshold_values(
                scale_ref=1.0,
                null_max=0.01,
                bridge_operator_error_max=0.02,
                signal_min=1.0,
                raw_relative_gap=1_000.0,
            )
        self.assertEqual(observed, expected)

        with mock.patch.object(
            thresholds,
            "any",
            create=True,
            return_value=True,
        ):
            with self.assertRaisesRegex(ValueError, "at least one t > 1"):
                preflight_source_bridge_work(
                    n_k=1,
                    n_trial=1,
                    steps=(1,),
                )

    def test_public_threshold_call_graph_has_no_global_loads(self):
        import rulespace_v3.thresholds as thresholds

        pending = [
            getattr(thresholds, name)
            for name in thresholds.__all__
            if inspect.isfunction(getattr(thresholds, name))
        ]
        seen: set[int] = set()
        offenders: list[tuple[str, str, object]] = []
        while pending:
            function = pending.pop()
            if id(function) in seen:
                continue
            seen.add(id(function))
            for instruction in dis.get_instructions(function):
                if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"}:
                    offenders.append(
                        (
                            function.__qualname__,
                            instruction.opname,
                            instruction.argval,
                        )
                    )
            reachable: list[object] = []
            reachable.extend(function.__defaults__ or ())
            reachable.extend((function.__kwdefaults__ or {}).values())
            reachable.extend(
                cell.cell_contents
                for cell in (function.__closure__ or ())
            )
            while reachable:
                value = reachable.pop()
                if (
                    inspect.isfunction(value)
                    and value.__module__ == thresholds.__name__
                ):
                    pending.append(value)
                elif type(value) in (tuple, list, frozenset):
                    reachable.extend(value)
                elif type(value) is dict:
                    reachable.extend(value.values())
        self.assertEqual(offenders, [])

    def test_protocol_threshold_verifier_ignores_public_constant_changes(self):
        import rulespace_v3.thresholds as thresholds

        with (
            mock.patch.object(thresholds, "T_CANDIDATES", (1,)),
            mock.patch.object(
                thresholds,
                "PHASE_GRID_PROTOCOL_ID",
                "caller-grid",
            ),
            mock.patch.object(
                thresholds,
                "PHASE_SEPARATION_PROTOCOL_ID",
                "caller-separation",
            ),
            mock.patch.object(thresholds, "SHELL_PARTICIPATION_MIN", 0.0),
            mock.patch.object(thresholds, "OVERLAP_MARGIN_MIN", 0.0),
            mock.patch.object(thresholds, "SHELL_LOOP_RESIDUAL_MAX", 1.0),
            mock.patch.object(
                thresholds,
                "SHELL_PROJECTOR_RESIDUAL_MAX",
                1.0,
            ),
        ):
            verify_window_protocol_thresholds(
                t_candidates=(256, 512, 1024, 2048, 4096, 8192),
                phase_grid_protocol_id="two-pi-over-16T-v1",
                phase_separation_protocol_id="eight-pi-over-T-v1",
                participation_min_required=0.25,
                overlap_margin_required=0.2,
                loop_residual_max=1.0e-10,
                projector_residual_max=1.0e-12,
            )

    def test_frozen_finiteness_check_ignores_math_module_monkeypatch(self):
        import rulespace_v3.thresholds as thresholds

        with mock.patch.object(
            thresholds.math,
            "isfinite",
            return_value=True,
        ):
            with self.assertRaisesRegex(ValueError, "finite"):
                verify_window_comparison_gates(
                    order=256,
                    phase_separation=phase_separation_min(256),
                    overlap_margin=float("inf"),
                    projector_t2t_distance=0.0,
                )


class WindowCalibrationProtocolTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.parent = issue_v3m0_parent_freeze()
        cls.shape5_controls = _quarter_turn_controls()
        cls.shape5_registry = build_closed_control_registry(
            cls.shape5_controls,
            cls.parent,
        )
        cls.controls = _window_controls()
        cls.registry = build_closed_control_registry(
            cls.controls,
            cls.parent,
        )

    @staticmethod
    def _resign_entry(
        entry: ControlWindowProtocolEntry,
        **changes: object,
    ) -> ControlWindowProtocolEntry:
        changed = object.__new__(ControlWindowProtocolEntry)
        for field in ControlWindowProtocolEntry.__dataclass_fields__:
            object.__setattr__(
                changed,
                field,
                changes.get(field, getattr(entry, field)),
            )
        object.__setattr__(changed, "entry_sha", "0" * 64)
        object.__setattr__(
            changed,
            "entry_sha",
            canonical_sha(control_window_protocol_entry_payload(changed)),
        )
        return changed

    @staticmethod
    def _resign_protocol(
        protocol: WindowCalibrationProtocol,
        **changes: object,
    ) -> WindowCalibrationProtocol:
        changed = object.__new__(WindowCalibrationProtocol)
        for field in WindowCalibrationProtocol.__dataclass_fields__:
            object.__setattr__(
                changed,
                field,
                changes.get(field, getattr(protocol, field)),
            )
        object.__setattr__(changed, "protocol_sha", "0" * 64)
        object.__setattr__(
            changed,
            "protocol_sha",
            canonical_sha(window_calibration_protocol_payload(changed)),
        )
        return changed

    def test_builder_freezes_registry_and_parent_application_protocols(self):
        entries = build_control_window_protocol_entries(self.registry)
        applications = (
            self.parent.manifest.synthetic_control_application_specs[:3]
        )
        self.assertEqual(
            tuple(entry.control_id for entry in entries),
            CONTROL_ORDER,
        )
        for entry, registry_entry, application in zip(
            entries,
            self.registry.registry.entries,
            applications,
        ):
            with self.subTest(control=entry.control_id):
                grid = application.grid_protocol
                self.assertEqual(
                    entry.control_registry_entry_sha,
                    registry_entry.entry_sha,
                )
                self.assertEqual(
                    entry.response_grid.reciprocal_indices,
                    grid.response_reciprocal_indices,
                )
                self.assertEqual(
                    entry.source_readout_bridge_grid.reciprocal_indices,
                    grid.bridge_reciprocal_indices,
                )
                self.assertEqual(
                    entry.source_readout_bridge_steps,
                    grid.bridge_steps,
                )
                self.assertEqual(
                    entry.reference_reciprocal_index,
                    grid.reference_reciprocal_index,
                )
                self.assertEqual(
                    entry.expected_shell_rank,
                    grid.expected_shell_rank,
                )
                self.assertEqual(
                    entry.expected_shell_rank_source_id,
                    grid.expected_shell_rank_source_id,
                )
                self.assertEqual(
                    entry.preregistered_phase_bands,
                    grid.preregistered_phase_bands,
                )

        verified = build_window_calibration_protocol(
            self.registry,
            entries,
        )
        self.assertIs(type(verified), VerifiedWindowCalibrationProtocol)
        raw = verified.protocol
        self.assertEqual(
            raw.protocol_schema_version,
            WINDOW_CALIBRATION_PROTOCOL_SCHEMA_VERSION,
        )
        self.assertEqual(
            raw.control_registry_sha,
            self.registry.registry.registry_sha,
        )
        self.assertEqual(
            raw.parent_freeze_sha,
            self.parent.manifest.parent_freeze_sha,
        )
        self.assertEqual(raw.t_candidates, T_CANDIDATES)
        self.assertEqual(raw.control_entries, entries)
        self.assertEqual(raw.participation_min_required, 0.25)
        self.assertEqual(raw.overlap_margin_required, 0.2)
        self.assertEqual(raw.loop_residual_max, 1.0e-10)
        self.assertEqual(raw.projector_residual_max, 1.0e-12)

    def test_registry_factory_shape_must_match_parent_application_grid(self):
        with self.assertRaisesRegex(ValueError, "spatial shape"):
            build_control_window_protocol_entries(self.shape5_registry)

    def test_raw_protocol_hydrates_only_against_live_registry_replay(self):
        entries = build_control_window_protocol_entries(self.registry)
        raw = build_window_calibration_protocol(
            self.registry,
            entries,
        ).protocol
        hydrated = verify_window_calibration_protocol(
            raw,
            self.registry,
        )
        self.assertIs(type(hydrated), VerifiedWindowCalibrationProtocol)
        self.assertEqual(hydrated.protocol, raw)

        fake_registry = object.__new__(VerifiedControlRegistry)
        with self.assertRaises((TypeError, ValueError)):
            verify_window_calibration_protocol(
                raw,
                fake_registry,
            )

    def test_resigned_registry_parent_threshold_and_entry_changes_fail_closed(self):
        entries = build_control_window_protocol_entries(self.registry)
        raw = build_window_calibration_protocol(
            self.registry,
            entries,
        ).protocol
        cases = (
            self._resign_protocol(
                raw,
                control_registry_sha="1" * 64,
            ),
            self._resign_protocol(
                raw,
                parent_freeze_sha="2" * 64,
            ),
            self._resign_protocol(
                raw,
                t_candidates=tuple(reversed(T_CANDIDATES)),
            ),
            self._resign_protocol(
                raw,
                participation_min_required=0.2,
            ),
            self._resign_protocol(
                raw,
                overlap_margin_required=0.25,
            ),
            self._resign_protocol(
                raw,
                loop_residual_max=2.0e-10,
            ),
            self._resign_protocol(
                raw,
                projector_residual_max=2.0e-12,
            ),
            self._resign_protocol(
                raw,
                control_entries=(
                    self._resign_entry(
                        entries[0],
                        expected_shell_rank=2,
                    ),
                    *entries[1:],
                ),
            ),
        )
        for changed in cases:
            with self.subTest(changed=changed):
                with self.assertRaises((TypeError, ValueError)):
                    verify_window_calibration_protocol(
                        changed,
                        self.registry,
                    )

    def test_resigned_nested_application_grid_change_fails_closed(self):
        entries = build_control_window_protocol_entries(self.registry)
        raw = build_window_calibration_protocol(
            self.registry,
            entries,
        ).protocol
        first = entries[0]
        response = first.response_grid
        direction = dataclasses.replace(
            response.direction_manifest,
            direction_ids=("counterfeit-direction",),
            direction_manifest_sha="0" * 64,
        )
        from rulespace_v3.grids import (
            direction_manifest_payload,
            response_grid_payload,
        )

        direction = dataclasses.replace(
            direction,
            direction_manifest_sha=canonical_sha(
                direction_manifest_payload(direction)
            ),
        )
        response = dataclasses.replace(
            response,
            direction_manifest=direction,
            response_grid_sha="0" * 64,
        )
        response = dataclasses.replace(
            response,
            response_grid_sha=canonical_sha(
                response_grid_payload(response)
            ),
        )
        first = self._resign_entry(first, response_grid=response)
        changed = self._resign_protocol(
            raw,
            control_entries=(first, *entries[1:]),
        )
        with self.assertRaises((TypeError, ValueError)):
            verify_window_calibration_protocol(
                changed,
                self.registry,
            )

    def test_fake_copied_and_slot_mutated_opaque_capabilities_fail_closed(self):
        entries = build_control_window_protocol_entries(self.registry)
        verified = build_window_calibration_protocol(
            self.registry,
            entries,
        )
        self.assertFalse(hasattr(verified, "__dict__"))
        with self.assertRaises(AttributeError):
            verified.protocol = verified.protocol  # type: ignore[misc]

        fake = object.__new__(VerifiedWindowCalibrationProtocol)
        with self.assertRaises((TypeError, ValueError)):
            _ = fake.protocol

        changed = self._resign_protocol(
            verified.protocol,
            overlap_margin_required=0.3,
        )
        object.__setattr__(
            verified,
            "_VerifiedWindowCalibrationProtocol__protocol",
            changed,
        )
        with self.assertRaises((TypeError, ValueError)):
            _ = verified.protocol

    def test_unknown_outer_and_nested_protocol_fields_fail_closed(self):
        entries = build_control_window_protocol_entries(self.registry)
        verified = build_window_calibration_protocol(
            self.registry,
            entries,
        )
        raw = verified.protocol
        object.__setattr__(raw, "caller_unknown", "forbidden")
        with self.assertRaises((TypeError, ValueError)):
            _ = verified.protocol

        verified = build_window_calibration_protocol(
            self.registry,
            entries,
        )
        raw = verified.protocol
        object.__setattr__(
            raw.control_entries[0],
            "caller_unknown",
            "forbidden",
        )
        with self.assertRaises((TypeError, ValueError)):
            _ = verified.protocol

    def test_live_authority_ignores_module_global_seal_monkeypatch(self):
        import rulespace_v3.window as window

        entries = build_control_window_protocol_entries(self.registry)
        verified = build_window_calibration_protocol(
            self.registry,
            entries,
        )
        raw = verified.protocol
        seal = object.__getattribute__(
            verified,
            "_VerifiedWindowCalibrationProtocol__seal",
        )
        object.__setattr__(
            raw,
            "overlap_margin_required",
            0.3,
        )
        with mock.patch.object(
            window,
            "_protocol_seal",
            return_value=seal,
        ):
            with self.assertRaises((TypeError, ValueError)):
                _ = verified.protocol

    def test_nested_unknown_field_cannot_bypass_rebound_exact_helper(self):
        import rulespace_v3.window as window

        entries = build_control_window_protocol_entries(self.registry)
        verified = build_window_calibration_protocol(
            self.registry,
            entries,
        )
        object.__setattr__(
            verified.protocol.control_entries[0].response_grid,
            "caller_unknown",
            "forbidden",
        )
        with mock.patch.object(
            window,
            "_require_exact_record_fields",
            return_value=None,
        ):
            with self.assertRaises((TypeError, ValueError)):
                _ = verified.protocol

    def test_issuance_hash_rebinding_cannot_create_a_live_zero_sha(self):
        import rulespace_v3.window as window

        with mock.patch.object(
            window,
            "canonical_sha",
            return_value="0" * 64,
        ):
            entries = build_control_window_protocol_entries(self.registry)
            verified = build_window_calibration_protocol(
                self.registry,
                entries,
            )
        self.assertNotEqual(verified.protocol.protocol_sha, "0" * 64)
        self.assertTrue(
            all(
                entry.entry_sha != "0" * 64
                for entry in verified.protocol.control_entries
            )
        )

    def test_issuance_threshold_rebinding_cannot_create_a_live_protocol(self):
        import rulespace_v3.window as window

        entries = build_control_window_protocol_entries(self.registry)
        with (
            mock.patch.object(window, "T_CANDIDATES", (1,)),
            mock.patch.object(window, "SHELL_PARTICIPATION_MIN", 0.0),
            mock.patch.object(window, "OVERLAP_MARGIN_MIN", 0.0),
            mock.patch.object(window, "SHELL_LOOP_RESIDUAL_MAX", 0.0),
            mock.patch.object(
                window,
                "SHELL_PROJECTOR_RESIDUAL_MAX",
                0.0,
            ),
            mock.patch.object(
                window,
                "verify_window_protocol_thresholds",
                return_value=None,
            ),
        ):
            verified = build_window_calibration_protocol(
                self.registry,
                entries,
            )
        self.assertEqual(verified.protocol.t_candidates, T_CANDIDATES)
        self.assertEqual(
            verified.protocol.participation_min_required,
            SHELL_PARTICIPATION_MIN,
        )
        self.assertEqual(
            verified.protocol.overlap_margin_required,
            OVERLAP_MARGIN_MIN,
        )

    def test_expected_entry_rebinding_cannot_sign_changed_reference(self):
        import rulespace_v3.window as window

        entries = build_control_window_protocol_entries(self.registry)
        changed_entries = tuple(
            self._resign_entry(
                entry,
                reference_reciprocal_index=(2,),
            )
            for entry in entries
        )
        with mock.patch.object(
            window,
            "_expected_control_entries",
            return_value=changed_entries,
        ):
            with self.assertRaises((TypeError, ValueError)):
                build_window_calibration_protocol(
                    self.registry,
                    changed_entries,
                )

    def test_grid_expected_body_rebinding_cannot_change_window_entries(self):
        import rulespace_v3.grids as grids

        entries = build_control_window_protocol_entries(self.registry)
        first_grid = entries[0].response_grid
        direction = dataclasses.replace(
            first_grid.direction_manifest,
            direction_ids=("forged-direction",),
            direction_manifest_sha="0" * 64,
        )
        from rulespace_v3.grids import (
            direction_manifest_payload,
            response_grid_payload,
        )

        direction = dataclasses.replace(
            direction,
            direction_manifest_sha=canonical_sha(
                direction_manifest_payload(direction)
            ),
        )
        forged = dataclasses.replace(
            first_grid,
            direction_manifest=direction,
            response_grid_sha="0" * 64,
        )
        forged = dataclasses.replace(
            forged,
            response_grid_sha=canonical_sha(
                response_grid_payload(forged)
            ),
        )
        with mock.patch.object(
            grids,
            "_expected_response_grid",
            return_value=forged,
        ):
            observed = build_control_window_protocol_entries(self.registry)
        self.assertEqual(observed, entries)

    def test_registry_view_rebinding_cannot_sign_a_zero_registry_sha(self):
        import types

        import rulespace_v3.registry as registry

        expected_sha = self.registry.registry.registry_sha

        def forged_view(**fields):
            return types.SimpleNamespace(
                registry=dataclasses.replace(
                    fields["registry"],
                    registry_sha="0" * 64,
                ),
                controls=fields["controls"],
                parent=fields["parent"],
            )

        with mock.patch.object(
            registry,
            "_VerifiedRegistryView",
            side_effect=forged_view,
        ):
            entries = build_control_window_protocol_entries(self.registry)
            verified = build_window_calibration_protocol(
                self.registry,
                entries,
            )
            observed_sha = verified.protocol.control_registry_sha
        self.assertEqual(observed_sha, expected_sha)

    def test_registry_hydrator_rejects_recursive_unknowns_and_subclasses(
        self,
    ):
        targets = (
            lambda raw: raw,
            lambda raw: raw.entries[0],
            lambda raw: raw.entries[0].source_basis,
            lambda raw: raw.entries[0].readout_calibration_spec,
            lambda raw: (
                raw.entries[0]
                .readout_calibration_spec
                .source_metric_whitener
            ),
        )
        for select in targets:
            raw = copy.deepcopy(self.registry.registry)
            object.__setattr__(
                select(raw),
                "caller_unknown",
                "forbidden",
            )
            with self.subTest(target=type(select(raw)).__name__):
                with self.assertRaisesRegex(
                    (TypeError, ValueError),
                    "exact|unknown|record type",
                ):
                    verify_closed_control_registry(
                        raw,
                        self.controls,
                        self.parent,
                    )

        class HostileRegistry(ClosedControlRegistry):
            pass

        raw = self.registry.registry
        hostile = HostileRegistry(
            raw.registry_schema_version,
            raw.entries,
            raw.parent_freeze_sha,
            raw.registry_sha,
        )
        with self.assertRaisesRegex(
            (TypeError, ValueError),
            "exact|record type|ClosedControlRegistry",
        ):
            verify_closed_control_registry(
                hostile,
                self.controls,
                self.parent,
            )

    def test_registry_hash_rebinding_cannot_transitively_sign_zero_authority(
        self,
    ):
        import rulespace_v3.registry as registry

        with (
            mock.patch.object(
                registry,
                "canonical_sha",
                return_value="0" * 64,
            ),
            mock.patch.object(
                registry,
                "control_registry_entry_payload",
                return_value={},
            ),
            mock.patch.object(
                registry,
                "closed_control_registry_payload",
                return_value={},
            ),
            mock.patch.object(
                registry,
                "_build_readout_spec",
                side_effect=AssertionError(
                    "mutable readout builder reached"
                ),
            ),
            mock.patch.object(
                registry,
                "_verify_bundle",
                side_effect=AssertionError(
                    "mutable bundle verifier reached"
                ),
            ),
        ):
            verified_registry = build_closed_control_registry(
                self.controls,
                self.parent,
            )
            entries = build_control_window_protocol_entries(
                verified_registry
            )
            verified_window = build_window_calibration_protocol(
                verified_registry,
                entries,
            )
        self.assertNotEqual(
            verified_registry.registry.registry_sha,
            "0" * 64,
        )
        self.assertNotEqual(
            verified_window.protocol.control_registry_sha,
            "0" * 64,
        )

    def test_registry_reverifier_has_no_module_global_loads(self):
        import rulespace_v3.registry as registry

        offenders = [
            (instruction.opname, instruction.argval)
            for instruction in dis.get_instructions(
                registry._reverify_verified_control_registry
            )
            if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"}
        ]
        self.assertEqual(offenders, [])

    def test_authority_snapshot_tamper_requires_closed_reconstruction(self):
        import rulespace_v3.window as window

        entries = build_control_window_protocol_entries(self.registry)
        verified = build_window_calibration_protocol(
            self.registry,
            entries,
        )
        raw = verified.protocol
        live_registry = next(
            cell.cell_contents
            for cell in (
                window._reverify_verified_window_calibration_protocol
                .__closure__
                or ()
            )
            if type(cell.cell_contents) is dict
            and id(verified) in cell.cell_contents
        )
        authority = live_registry[id(verified)][1]
        object.__setattr__(raw, "overlap_margin_required", 0.0)
        object.__setattr__(
            authority.protocol_snapshot,
            "overlap_margin_required",
            0.0,
        )
        with self.assertRaises((TypeError, ValueError)):
            _ = verified.protocol

    def test_window_public_authority_call_graph_has_no_global_loads(self):
        import rulespace_v3.window as window

        pending = [
            window.build_control_window_protocol_entries,
            window.build_window_calibration_protocol,
            window.verify_window_calibration_protocol,
            VerifiedWindowCalibrationProtocol.protocol.fget,
        ]
        seen: set[int] = set()
        offenders: list[tuple[str, str, object]] = []
        while pending:
            function = pending.pop()
            if function is None or id(function) in seen:
                continue
            seen.add(id(function))
            for instruction in dis.get_instructions(function):
                if instruction.opname in {"LOAD_GLOBAL", "LOAD_NAME"}:
                    offenders.append(
                        (
                            function.__qualname__,
                            instruction.opname,
                            instruction.argval,
                        )
                    )
            reachable: list[object] = []
            reachable.extend(function.__defaults__ or ())
            reachable.extend((function.__kwdefaults__ or {}).values())
            reachable.extend(
                cell.cell_contents
                for cell in (function.__closure__ or ())
            )
            while reachable:
                value = reachable.pop()
                if (
                    inspect.isfunction(value)
                    and value.__module__ == window.__name__
                ):
                    pending.append(value)
                elif type(value) in (tuple, list, frozenset):
                    reachable.extend(value)
                elif type(value) is dict:
                    reachable.extend(value.values())
        self.assertEqual(offenders, [])

    def test_protocol_input_cap_rejects_before_registry_replay(self):
        entries = build_control_window_protocol_entries(self.registry)
        with mock.patch(
            "rulespace_v3.window._reverify_verified_control_registry"
        ) as replay:
            with self.assertRaisesRegex(ValueError, "exactly three"):
                build_window_calibration_protocol(
                    self.registry,
                    entries + (entries[0],),
                )
        replay.assert_not_called()

    def test_nested_direction_cap_precedes_registry_replay_and_hash(self):
        entries = build_control_window_protocol_entries(self.registry)
        raw = build_window_calibration_protocol(
            self.registry,
            entries,
        ).protocol
        first = entries[0]
        direction = object.__new__(type(first.response_grid.direction_manifest))
        for field in type(direction).__dataclass_fields__:
            object.__setattr__(
                direction,
                field,
                getattr(first.response_grid.direction_manifest, field),
            )
        object.__setattr__(
            direction,
            "direction_ids",
            ("direction",) * (262_144 + 1),
        )
        response = object.__new__(type(first.response_grid))
        for field in type(response).__dataclass_fields__:
            object.__setattr__(
                response,
                field,
                getattr(first.response_grid, field),
            )
        object.__setattr__(response, "direction_manifest", direction)
        changed_entry = object.__new__(type(first))
        for field in type(first).__dataclass_fields__:
            object.__setattr__(
                changed_entry,
                field,
                getattr(first, field),
            )
        object.__setattr__(changed_entry, "response_grid", response)
        changed = object.__new__(type(raw))
        for field in type(raw).__dataclass_fields__:
            object.__setattr__(changed, field, getattr(raw, field))
        object.__setattr__(
            changed,
            "control_entries",
            (changed_entry,) + entries[1:],
        )
        with (
            mock.patch(
                "rulespace_v3.window._reverify_verified_control_registry",
                side_effect=AssertionError("registry replay before caps"),
            ) as replay,
            mock.patch(
                "rulespace_v3.window.canonical_sha",
                side_effect=AssertionError("hash before caps"),
            ) as hasher,
        ):
            with self.assertRaisesRegex(ValueError, "directions.*point cap"):
                verify_window_calibration_protocol(
                    changed,
                    self.registry,
                )
        replay.assert_not_called()
        hasher.assert_not_called()

    def test_protocol_text_cap_precedes_registry_replay_and_hash(self):
        raw = build_window_calibration_protocol(
            self.registry,
            build_control_window_protocol_entries(self.registry),
        ).protocol
        changed = object.__new__(WindowCalibrationProtocol)
        for field in WindowCalibrationProtocol.__dataclass_fields__:
            object.__setattr__(changed, field, getattr(raw, field))
        object.__setattr__(
            changed,
            "protocol_schema_version",
            "x" * (GENERAL_EVIDENCE_TEXT_BYTES_MAX + 1),
        )
        with (
            mock.patch(
                "rulespace_v3.window._reverify_verified_control_registry",
                side_effect=AssertionError("registry replay before text cap"),
            ) as replay,
            mock.patch(
                "rulespace_v3.window.canonical_sha",
                side_effect=AssertionError("hash before text cap"),
            ) as hasher,
        ):
            with self.assertRaisesRegex(ValueError, "text.*resource cap"):
                verify_window_calibration_protocol(
                    changed,
                    self.registry,
                )
        replay.assert_not_called()
        hasher.assert_not_called()

    def test_protocol_utf8_text_byte_cap_precedes_replay_and_hash(self):
        import rulespace_v3.window as window

        entries = build_control_window_protocol_entries(self.registry)
        raw = build_window_calibration_protocol(
            self.registry,
            entries,
        ).protocol
        first = entries[0]
        direction = object.__new__(
            type(first.response_grid.direction_manifest)
        )
        for field in type(direction).__dataclass_fields__:
            object.__setattr__(
                direction,
                field,
                getattr(first.response_grid.direction_manifest, field),
            )
        object.__setattr__(
            direction,
            "direction_ids",
            ("😀" * 5_000,),
        )
        response = object.__new__(type(first.response_grid))
        for field in type(response).__dataclass_fields__:
            object.__setattr__(
                response,
                field,
                getattr(first.response_grid, field),
            )
        object.__setattr__(response, "direction_manifest", direction)
        changed_entry = object.__new__(type(first))
        for field in type(first).__dataclass_fields__:
            object.__setattr__(
                changed_entry,
                field,
                getattr(first, field),
            )
        object.__setattr__(changed_entry, "response_grid", response)
        changed = object.__new__(type(raw))
        for field in type(raw).__dataclass_fields__:
            object.__setattr__(changed, field, getattr(raw, field))
        object.__setattr__(
            changed,
            "control_entries",
            (changed_entry,) + entries[1:],
        )
        with (
            mock.patch.object(
                window,
                "_reverify_verified_control_registry",
                side_effect=AssertionError(
                    "registry replay before UTF-8 text cap"
                ),
            ) as replay,
            mock.patch.object(
                window,
                "canonical_sha",
                side_effect=AssertionError("hash before UTF-8 text cap"),
            ) as hasher,
        ):
            with self.assertRaisesRegex(ValueError, "text.*resource cap"):
                verify_window_calibration_protocol(
                    changed,
                    self.registry,
                )
        replay.assert_not_called()
        hasher.assert_not_called()

    def test_nested_dimension_cap_precedes_registry_replay_and_hash(self):
        entries = build_control_window_protocol_entries(self.registry)
        raw = build_window_calibration_protocol(
            self.registry,
            entries,
        ).protocol
        first = entries[0]
        response = object.__new__(type(first.response_grid))
        for field in type(response).__dataclass_fields__:
            object.__setattr__(
                response,
                field,
                getattr(first.response_grid, field),
            )
        object.__setattr__(
            response,
            "spatial_ndim",
            GENERAL_EVIDENCE_SPATIAL_NDIM_MAX + 1,
        )
        object.__setattr__(
            response,
            "torus_denominators",
            (8,) * (GENERAL_EVIDENCE_SPATIAL_NDIM_MAX + 1),
        )
        changed_entry = object.__new__(type(first))
        for field in type(first).__dataclass_fields__:
            object.__setattr__(
                changed_entry,
                field,
                getattr(first, field),
            )
        object.__setattr__(changed_entry, "response_grid", response)
        changed = object.__new__(type(raw))
        for field in type(raw).__dataclass_fields__:
            object.__setattr__(changed, field, getattr(raw, field))
        object.__setattr__(
            changed,
            "control_entries",
            (changed_entry,) + entries[1:],
        )
        with (
            mock.patch(
                "rulespace_v3.window._reverify_verified_control_registry",
                side_effect=AssertionError(
                    "registry replay before dimension cap"
                ),
            ) as replay,
            mock.patch(
                "rulespace_v3.window.canonical_sha",
                side_effect=AssertionError("hash before dimension cap"),
            ) as hasher,
        ):
            with self.assertRaisesRegex(ValueError, "dimension.*resource cap"):
                verify_window_calibration_protocol(
                    changed,
                    self.registry,
                )
        replay.assert_not_called()
        hasher.assert_not_called()

    def test_streamed_protocol_upper_bound_precedes_replay_and_hash(self):
        entries = build_control_window_protocol_entries(self.registry)
        raw = build_window_calibration_protocol(
            self.registry,
            entries,
        ).protocol
        first = entries[0]
        direction = object.__new__(
            type(first.response_grid.direction_manifest)
        )
        for field in type(direction).__dataclass_fields__:
            object.__setattr__(
                direction,
                field,
                getattr(first.response_grid.direction_manifest, field),
            )
        shared_text = "x" * GENERAL_EVIDENCE_TEXT_BYTES_MAX
        object.__setattr__(
            direction,
            "direction_ids",
            (shared_text,) * 2_731,
        )
        response = object.__new__(type(first.response_grid))
        for field in type(response).__dataclass_fields__:
            object.__setattr__(
                response,
                field,
                getattr(first.response_grid, field),
            )
        object.__setattr__(
            response,
            "direction_manifest",
            direction,
        )
        changed_entry = object.__new__(type(first))
        for field in type(first).__dataclass_fields__:
            object.__setattr__(
                changed_entry,
                field,
                getattr(first, field),
            )
        object.__setattr__(changed_entry, "response_grid", response)
        changed = object.__new__(type(raw))
        for field in type(raw).__dataclass_fields__:
            object.__setattr__(changed, field, getattr(raw, field))
        object.__setattr__(
            changed,
            "control_entries",
            (changed_entry,) + entries[1:],
        )
        with (
            mock.patch(
                "rulespace_v3.window._reverify_verified_control_registry",
                side_effect=AssertionError(
                    "registry replay before serialized cap"
                ),
            ) as replay,
            mock.patch(
                "rulespace_v3.window.canonical_sha",
                side_effect=AssertionError("hash before serialized cap"),
            ) as hasher,
        ):
            with self.assertRaisesRegex(
                ValueError,
                "serialized body.*resource cap",
            ):
                verify_window_calibration_protocol(
                    changed,
                    self.registry,
                )
        replay.assert_not_called()
        hasher.assert_not_called()

    def test_combined_three_entry_cap_precedes_any_record_post_init(self):
        import rulespace_v3.grids as grids

        entries = build_control_window_protocol_entries(self.registry)
        first = entries[0]
        direction = object.__new__(
            type(first.response_grid.direction_manifest)
        )
        for field in type(direction).__dataclass_fields__:
            object.__setattr__(
                direction,
                field,
                getattr(first.response_grid.direction_manifest, field),
            )
        shared_text = "x" * GENERAL_EVIDENCE_TEXT_BYTES_MAX
        object.__setattr__(
            direction,
            "direction_ids",
            (shared_text,) * 1_024,
        )
        response = object.__new__(type(first.response_grid))
        for field in type(response).__dataclass_fields__:
            object.__setattr__(
                response,
                field,
                getattr(first.response_grid, field),
            )
        object.__setattr__(response, "direction_manifest", direction)
        changed_entry = object.__new__(type(first))
        for field in type(first).__dataclass_fields__:
            object.__setattr__(
                changed_entry,
                field,
                getattr(first, field),
            )
        object.__setattr__(changed_entry, "response_grid", response)
        large_entries = (changed_entry,) * 3
        raw = build_window_calibration_protocol(
            self.registry,
            entries,
        ).protocol
        changed = object.__new__(type(raw))
        for field in type(raw).__dataclass_fields__:
            object.__setattr__(changed, field, getattr(raw, field))
        object.__setattr__(changed, "control_entries", large_entries)

        calls = (
            lambda: build_window_calibration_protocol(
                self.registry,
                large_entries,
            ),
            lambda: verify_window_calibration_protocol(
                changed,
                self.registry,
            ),
        )
        for callback in calls:
            with self.subTest(callback=callback):
                with mock.patch.object(
                    grids.ResponseKGridManifest,
                    "__post_init__",
                    side_effect=AssertionError(
                        "record post-init before combined entry cap"
                    ),
                ) as post_init:
                    with self.assertRaisesRegex(
                        ValueError,
                        "serialized body.*resource cap",
                    ):
                        callback()
                post_init.assert_not_called()

    def test_task11a_does_not_publish_complete_calibration_outcome(self):
        import rulespace_v3.window as window

        forbidden = {
            "WindowCalibrationOutcome",
            "WindowThresholdSelection",
            "VerifiedWindowThresholdCalibration",
            "calibrate_window_and_thresholds",
            "verify_window_threshold_calibration",
        }
        self.assertTrue(forbidden.isdisjoint(vars(window)))

    def test_protocol_records_and_payloads_have_exact_wire_fields(self):
        entries = build_control_window_protocol_entries(self.registry)
        raw = build_window_calibration_protocol(
            self.registry,
            entries,
        ).protocol
        self.assertEqual(
            tuple(ControlWindowProtocolEntry.__dataclass_fields__),
            (
                "control_id",
                "control_registry_entry_sha",
                "response_grid",
                "source_readout_bridge_grid",
                "source_readout_bridge_steps",
                "reference_reciprocal_index",
                "expected_shell_rank",
                "expected_shell_rank_source_id",
                "preregistered_phase_bands",
                "source_trial_generation_id",
                "entry_sha",
            ),
        )
        self.assertEqual(
            tuple(WindowCalibrationProtocol.__dataclass_fields__),
            (
                "protocol_schema_version",
                "control_registry_sha",
                "parent_freeze_sha",
                "t_candidates",
                "control_entries",
                "phase_grid_protocol_id",
                "phase_separation_protocol_id",
                "participation_min_required",
                "overlap_margin_required",
                "loop_residual_max",
                "projector_residual_max",
                "protocol_sha",
            ),
        )
        self.assertEqual(
            tuple(control_window_protocol_entry_payload(entries[0])),
            tuple(ControlWindowProtocolEntry.__dataclass_fields__)[:-1],
        )
        self.assertEqual(
            tuple(window_calibration_protocol_payload(raw)),
            tuple(WindowCalibrationProtocol.__dataclass_fields__)[:-1],
        )


if __name__ == "__main__":
    unittest.main()
