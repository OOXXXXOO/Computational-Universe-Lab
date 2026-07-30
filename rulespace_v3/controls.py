"""Synthetic anchor triangle built from the same local primitive API."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Sequence

import numpy as np
import sympy as sp

from .factory import (
    BasisManifest,
    CalibrationObservation,
    CalibrationSeed,
    FrozenSyntheticTarget,
    PrimitiveInterface,
    PrimitiveOperatorWire,
    VerifiedFactory,
    basis_manifest_array,
    build_basis_manifest,
    build_factory_from_trace,
    build_full_factory_from_seed,
    calibration_observation_payload,
    calibration_seed_payload,
    measure_calibration_holdout,
    synthetic_target_payload,
    verify_synthetic_target,
)
from .evidence import canonical_sha
from .trace import (
    ConstructionTrace,
    PrimitiveSpec,
    ProvenanceNode,
    ProvenanceOperation,
    build_construction_trace,
)


CONTROL_SCHEMA_VERSION = "v3m0.synthetic-control-bundle.v1"
_SOURCE_SHA = "c" * 64


@dataclass(frozen=True)
class SyntheticControlBundle:
    control_schema_version: str
    control_id: Literal["full", "zero", "direct_sum"]
    mode_count: int
    target: FrozenSyntheticTarget
    construction_trace: ConstructionTrace
    factory: VerifiedFactory
    source_basis: BasisManifest
    expected_actual_rank: int
    expected_ablated_rank: int

    def __post_init__(self) -> None:
        if self.control_schema_version != CONTROL_SCHEMA_VERSION:
            raise ValueError("unexpected control_schema_version")
        if self.control_id not in ("full", "zero", "direct_sum"):
            raise ValueError("unknown control_id")
        if type(self.mode_count) is not int or self.mode_count <= 0:
            raise ValueError("mode_count must be a positive int")
        if not isinstance(self.target, FrozenSyntheticTarget):
            raise TypeError("target must be a FrozenSyntheticTarget")
        if not isinstance(self.construction_trace, ConstructionTrace):
            raise TypeError("construction_trace must be a ConstructionTrace")
        if not isinstance(self.factory, VerifiedFactory):
            raise TypeError("factory must be a VerifiedFactory")
        if not isinstance(self.source_basis, BasisManifest):
            raise TypeError("source_basis must be a BasisManifest")
        for field in ("expected_actual_rank", "expected_ablated_rank"):
            value = getattr(self, field)
            if type(value) is not int or value < 0:
                raise ValueError(f"{field} must be a non-negative int")


def _mode_count(value: object) -> int:
    if type(value) is not int:
        raise TypeError("mode_count must be an int")
    if value <= 0:
        raise ValueError("mode_count must be positive")
    return value


def _spatial_shape(value: Sequence[int]) -> tuple[int, ...]:
    shape = tuple(value)
    if not shape:
        raise ValueError("spatial_shape must be non-empty")
    for index, length in enumerate(shape):
        if type(length) is not int or length <= 0:
            raise ValueError(f"spatial_shape[{index}] must be a positive int")
    return shape


def _canonical_channels(mode_count: int) -> tuple[str, ...]:
    return tuple(
        channel
        for mode in range(mode_count)
        for channel in (f"x.{mode:03d}", f"y.{mode:03d}")
    )


def _canonical_basis(
    interface: PrimitiveInterface,
    source_indices: Sequence[int],
    readout_indices: Sequence[int],
) -> tuple[BasisManifest, BasisManifest]:
    source = np.zeros(
        (len(tuple(source_indices)), len(interface.channel_order)),
        dtype=np.complex128,
    )
    for row, channel in enumerate(source_indices):
        source[row, channel] = 1.0
    readout = np.zeros(
        (len(tuple(readout_indices)), len(interface.channel_order)),
        dtype=np.complex128,
    )
    for row, channel in enumerate(readout_indices):
        readout[row, channel] = 1.0
    return (
        build_basis_manifest(
            role="source",
            state_schema_id=interface.state_schema_id,
            channel_order=interface.channel_order,
            vectors=source,
        ),
        build_basis_manifest(
            role="readout",
            state_schema_id=interface.state_schema_id,
            channel_order=interface.channel_order,
            vectors=readout,
        ),
    )


def _operator_for_pair(
    *,
    pair_index: int,
    x_channel: str,
    y_channel: str,
    interface: PrimitiveInterface,
    conditioned: bool,
) -> tuple[PrimitiveOperatorWire, ...]:
    production = (
        "target_operator" if conditioned else "local_canonical_shear"
    )
    coefficients = (1.0, -1.0, 1.0)
    sources = (x_channel, y_channel, x_channel)
    destinations = (y_channel, x_channel, y_channel)
    return tuple(
        PrimitiveOperatorWire(
            mechanism_id=f"pair.{pair_index:03d}.shear.{layer}",
            production_id=production,
            layer_slot_id=f"layer.{pair_index:03d}.{layer}",
            operation_id="local_canonical_shear",
            interface_id=interface.interface_id,
            source_channel=sources[layer],
            destination_channel=destinations[layer],
            offset=(0,) * interface.spatial_ndim,
            coefficient_wire=(coefficients[layer], 0.0),
        )
        for layer in range(3)
    )


def _trace_for_operators(
    operators: Sequence[PrimitiveOperatorWire],
    target: FrozenSyntheticTarget,
    conditioned_mechanisms: frozenset[str],
) -> ConstructionTrace:
    nodes = []
    specifications = []
    for index, operator in enumerate(operators):
        conditioned = operator.mechanism_id in conditioned_mechanisms
        provenance_id = f"primitive.provenance.{index:06d}"
        nodes.append(
            ProvenanceNode(
                provenance_id=provenance_id,
                operation=(
                    ProvenanceOperation.TARGET_SPEC_READ
                    if conditioned
                    else ProvenanceOperation.GRAMMAR_PRIMITIVE
                ),
                depends_on=(),
                target_refs=(
                    (f"target:{target.target_spec_id}",)
                    if conditioned
                    else ()
                ),
                objective_tags=(),
                search_run_id=None,
                source_sha=_SOURCE_SHA,
            )
        )
        coefficient = sp.Integer(int(operator.coefficient_wire[0]))
        if operator.coefficient_wire[1]:
            coefficient += sp.I * sp.Integer(
                int(operator.coefficient_wire[1])
            )
        zero = (0,) * len(operator.offset)
        specifications.append(
            PrimitiveSpec(
                mechanism_id=operator.mechanism_id,
                production_id=operator.production_id,
                depends_on=(),
                support_offsets=tuple(sorted({zero, operator.offset})),
                state_channels=tuple(
                    sorted(
                        (
                            operator.source_channel,
                            operator.destination_channel,
                        )
                    )
                ),
                coefficient_expression=coefficient,
                coefficient_variable_order=(),
                symbolic_origin_tags=(),
                neutral_ablation="neutral-identity-v1",
                design_objective_tags=(),
                search_run_id=None,
                source_sha=_SOURCE_SHA,
                design_provenance=provenance_id,
            )
        )
    return build_construction_trace(
        target_spec_id=target.target_spec_id,
        provenance_nodes=tuple(nodes),
        primitive_specs=tuple(specifications),
    )


def _control_factory(
    *,
    mode_count: int,
    target: FrozenSyntheticTarget,
    spatial_shape: Sequence[int],
    dt: float,
    channels: tuple[str, ...],
    operators: tuple[PrimitiveOperatorWire, ...],
    conditioned_mechanisms: frozenset[str],
    control_id: Literal["zero", "direct_sum"],
    expected_actual_rank: int,
    expected_ablated_rank: int,
) -> SyntheticControlBundle:
    verified_target = verify_synthetic_target(target)
    shape = _spatial_shape(spatial_shape)
    interface = PrimitiveInterface(
        interface_id="interface.synthetic.local-linear.v1",
        state_schema_id="state.synthetic.local-linear.v1",
        spatial_ndim=len(shape),
        channel_order=channels,
        dtype="complex128",
        backend="numpy",
    )
    source_indices = tuple(range(0, len(channels), 2))
    readout_indices = tuple(range(1, len(channels), 2))
    source, readout = _canonical_basis(
        interface,
        source_indices,
        readout_indices,
    )
    trace = _trace_for_operators(
        operators,
        verified_target,
        conditioned_mechanisms,
    )
    factory = build_factory_from_trace(
        trace,
        verified_target,
        factory_id="synthetic.local-linear.factory.v1",
        interface=interface,
        state_shape=(len(channels),) + shape,
        dt=dt,
        target_blind_parameters=(),
        layer_slot_ids=tuple(item.layer_slot_id for item in operators),
        operator_payload=operators,
        source_manifest_id=source.manifest_id,
        readout_basis=readout,
        boundary_manifest_id="periodic-v1",
    )
    return SyntheticControlBundle(
        control_schema_version=CONTROL_SCHEMA_VERSION,
        control_id=control_id,
        mode_count=mode_count,
        target=verified_target,
        construction_trace=trace,
        factory=factory,
        source_basis=source,
        expected_actual_rank=expected_actual_rank,
        expected_ablated_rank=expected_ablated_rank,
    )


def build_full_control(
    seed: CalibrationSeed,
    observation: CalibrationObservation,
    target: FrozenSyntheticTarget,
) -> SyntheticControlBundle:
    """Bind the target-free calibration operator to the frozen observation."""

    if not isinstance(seed, CalibrationSeed):
        raise TypeError("seed must be a CalibrationSeed")
    if not isinstance(observation, CalibrationObservation):
        raise TypeError("observation must be a CalibrationObservation")
    if not isinstance(target, FrozenSyntheticTarget):
        raise TypeError("target must be a FrozenSyntheticTarget")
    verified_target = verify_synthetic_target(target)
    if seed.seed_sha != canonical_sha(calibration_seed_payload(seed)):
        raise ValueError("seed_sha mismatch")
    if observation.observation_sha != canonical_sha(
        calibration_observation_payload(observation)
    ):
        raise ValueError("observation_sha mismatch")
    if verified_target.observation != observation:
        raise ValueError("target does not embed the supplied observation")
    if verified_target.target_spec_sha != canonical_sha(
        synthetic_target_payload(verified_target)
    ):
        raise ValueError("target_spec_sha mismatch")
    expected_channels = _canonical_channels(
        len(seed.source_basis.vectors_wire)
    )
    if seed.interface.channel_order != expected_channels:
        raise ValueError("FULL seed channel_order is not canonical")
    mode_count = len(seed.source_basis.vectors_wire)
    if len(seed.readout_basis.vectors_wire) != mode_count:
        raise ValueError("FULL source/readout mode count mismatch")
    expected_source = np.zeros(
        (mode_count, len(expected_channels)),
        dtype=np.complex128,
    )
    expected_readout = np.zeros_like(expected_source)
    for mode in range(mode_count):
        expected_source[mode, 2 * mode] = 1.0
        expected_readout[mode, 2 * mode + 1] = 1.0
    if not np.array_equal(
        basis_manifest_array(seed.source_basis),
        expected_source,
    ):
        raise ValueError("FULL canonical source basis mismatch")
    if not np.array_equal(
        basis_manifest_array(seed.readout_basis),
        expected_readout,
    ):
        raise ValueError("FULL canonical readout basis mismatch")
    if len(seed.runtime_operator_payload) != 3 * mode_count:
        raise ValueError("FULL requires one three-shear quarter-turn per mode")
    expected_coefficients = ((1.0, 0.0), (-1.0, 0.0), (1.0, 0.0))
    for mode in range(mode_count):
        x_channel = expected_channels[2 * mode]
        y_channel = expected_channels[2 * mode + 1]
        expected_sources = (x_channel, y_channel, x_channel)
        expected_destinations = (y_channel, x_channel, y_channel)
        for layer, operator in enumerate(
            seed.runtime_operator_payload[3 * mode : 3 * mode + 3]
        ):
            if (
                operator.production_id != "local_canonical_shear"
                or operator.operation_id != "local_canonical_shear"
                or operator.source_channel != expected_sources[layer]
                or operator.destination_channel
                != expected_destinations[layer]
                or operator.offset != (0,) * seed.interface.spatial_ndim
                or operator.coefficient_wire != expected_coefficients[layer]
            ):
                raise ValueError(
                    "FULL requires one three-shear quarter-turn per mode"
                )
    if observation != measure_calibration_holdout(seed):
        raise ValueError("observation is not the seed hold-out observation")
    trace = _trace_for_operators(
        seed.runtime_operator_payload,
        verified_target,
        frozenset(),
    )
    factory = build_full_factory_from_seed(
        trace,
        verified_target,
        seed,
        factory_id="synthetic.local-linear.factory.v1",
        layer_slot_ids=tuple(
            item.layer_slot_id for item in seed.runtime_operator_payload
        ),
    )
    return SyntheticControlBundle(
        control_schema_version=CONTROL_SCHEMA_VERSION,
        control_id="full",
        mode_count=mode_count,
        target=verified_target,
        construction_trace=trace,
        factory=factory,
        source_basis=seed.source_basis,
        expected_actual_rank=mode_count,
        expected_ablated_rank=mode_count,
    )


def build_zero_control(
    mode_count: int,
    target: FrozenSyntheticTarget,
    spatial_shape: Sequence[int],
    dt: float,
) -> SyntheticControlBundle:
    count = _mode_count(mode_count)
    shape = _spatial_shape(spatial_shape)
    channels = _canonical_channels(count)
    interface = PrimitiveInterface(
        interface_id="interface.synthetic.local-linear.v1",
        state_schema_id="state.synthetic.local-linear.v1",
        spatial_ndim=len(shape),
        channel_order=channels,
        dtype="complex128",
        backend="numpy",
    )
    operators = tuple(
        operator
        for mode in range(count)
        for operator in _operator_for_pair(
            pair_index=mode,
            x_channel=channels[2 * mode],
            y_channel=channels[2 * mode + 1],
            interface=interface,
            conditioned=True,
        )
    )
    return _control_factory(
        mode_count=count,
        target=target,
        spatial_shape=shape,
        dt=dt,
        channels=channels,
        operators=operators,
        conditioned_mechanisms=frozenset(
            item.mechanism_id for item in operators
        ),
        control_id="zero",
        expected_actual_rank=count,
        expected_ablated_rank=0,
    )


def build_direct_sum_control(
    mode_count: int,
    target: FrozenSyntheticTarget,
    spatial_shape: Sequence[int],
    dt: float,
) -> SyntheticControlBundle:
    count = _mode_count(mode_count)
    shape = _spatial_shape(spatial_shape)
    blind_channels = tuple(
        channel
        for mode in range(count)
        for channel in (f"x.b.{mode:03d}", f"y.b.{mode:03d}")
    )
    conditioned_channels = tuple(
        channel
        for mode in range(count, 2 * count)
        for channel in (f"x.c.{mode:03d}", f"y.c.{mode:03d}")
    )
    channels = blind_channels + conditioned_channels
    interface = PrimitiveInterface(
        interface_id="interface.synthetic.local-linear.v1",
        state_schema_id="state.synthetic.local-linear.v1",
        spatial_ndim=len(shape),
        channel_order=channels,
        dtype="complex128",
        backend="numpy",
    )
    blind = tuple(
        operator
        for mode in range(count)
        for operator in _operator_for_pair(
            pair_index=mode,
            x_channel=blind_channels[2 * mode],
            y_channel=blind_channels[2 * mode + 1],
            interface=interface,
            conditioned=False,
        )
    )
    conditioned = tuple(
        operator
        for local_mode, global_mode in enumerate(range(count, 2 * count))
        for operator in _operator_for_pair(
            pair_index=global_mode,
            x_channel=conditioned_channels[2 * local_mode],
            y_channel=conditioned_channels[2 * local_mode + 1],
            interface=interface,
            conditioned=True,
        )
    )
    operators = blind + conditioned
    return _control_factory(
        mode_count=count,
        target=target,
        spatial_shape=shape,
        dt=dt,
        channels=channels,
        operators=operators,
        conditioned_mechanisms=frozenset(
            item.mechanism_id for item in conditioned
        ),
        control_id="direct_sum",
        expected_actual_rank=2 * count,
        expected_ablated_rank=count,
    )


__all__ = [
    "CONTROL_SCHEMA_VERSION",
    "SyntheticControlBundle",
    "build_direct_sum_control",
    "build_full_control",
    "build_zero_control",
]
