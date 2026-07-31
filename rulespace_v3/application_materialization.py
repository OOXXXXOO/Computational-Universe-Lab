"""Scenario-bound C06--C12 local application materialization.

This module stops at a live, replayable recipe/factory binding.  It does not
issue application evidence, paired responses, response blocks, or any
scientific PASS capability.
"""

from __future__ import annotations

import re
import threading
import weakref
from dataclasses import dataclass, replace

import numpy as np

from .ablation import (
    AblationConstructionOutcome,
    _verify_construction_outcome,
    matched_ablation,
)
from .application_recipes import (
    APPLICATION_RECIPE_SCENARIO_IDS,
    ApplicationLocalShearStep,
    ApplicationOperationEffect,
    ApplicationRecipeArtifact,
    build_application_recipe,
    build_application_recipe_trace_and_operators,
)
from .calibration_authority import (
    CalibrationApplicationPermit,
    SelectedControlEvidenceRef,
    VerifiedCalibrationApplicationPermit,
    WindowThresholdCalibrationManifest,
    WindowThresholdSelection,
    _UPSTREAM_TASK12_WIRE_TYPES,
    _candidate_record_types,
    _exact_record,
    _payload_without_hash,
    _preflight_tree,
    _reverify_verified_calibration_application_permit,
    _reverify_verified_window_threshold_calibration,
)
from .contracts import UndefinedReason
from .evidence import _make_exact_wire_cloner, canonical_sha
from .factory import (
    BasisManifest,
    FrozenComplexTensor,
    FrozenSyntheticTarget,
    PrimitiveInterface,
    PrimitiveOperatorWire,
    VerifiedFactory,
    _reverify_verified_factory,
    build_basis_manifest,
    build_factory_from_trace,
    freeze_complex_tensor,
    frozen_tensor_array,
)
from .grids import BridgeKGridManifest, ResponseKGridManifest
from .parent_freeze import (
    ApplicationScenarioExecutionSpec,
)
from .pair_snapshot import AblationPairSnapshot, _pair_snapshot
from .registry import _reverify_verified_control_registry
from .thresholds import BRIDGE_TOLERANCE, T_CANDIDATES
from .trace import (
    CoefficientRecord,
    ConstructionTrace,
    MechanismKind,
    PrimitiveTrace,
    ProvenanceNode,
    ProvenanceOperation,
)


APPLICATION_SCENARIO_RUN_SPEC_SCHEMA_VERSION = (
    "v3m0.application-scenario-run-spec.v1"
)
APPLICATION_SCENARIO_MATERIALIZATION_SCHEMA_VERSION = (
    "v3m0.application-scenario-materialization.v1"
)

_ALLOWED_SCENARIOS = frozenset(APPLICATION_RECIPE_SCENARIO_IDS)
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_ISSUANCE_TOKEN = object()


def _text(value: object, field: str) -> str:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if not value.strip():
        raise ValueError(f"{field} must be non-empty")
    return value


def _sha(value: object, field: str) -> str:
    result = _text(value, field)
    if _LOWER_SHA.fullmatch(result) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return result


@dataclass(frozen=True)
class ApplicationScenarioRunSpec:
    """Response inputs derived for one exact permit scenario."""

    run_spec_schema_version: str
    permit_sha: str
    application_spec_sha: str
    scenario_id: str
    scenario_sha: str
    fejer_order: int
    source_basis: BasisManifest
    readout_basis: BasisManifest
    response_grid: ResponseKGridManifest
    source_readout_bridge_grid: BridgeKGridManifest
    source_readout_bridge_steps: tuple[int, ...]
    reference_reciprocal_index: tuple[int, ...]
    preregistered_phase_bands: tuple[tuple[float, float], ...]
    expected_shell_rank: int
    source_trial_vectors: FrozenComplexTensor
    bridge_tolerance: float
    run_spec_sha: str

    def __post_init__(self) -> None:
        if (
            self.run_spec_schema_version
            != APPLICATION_SCENARIO_RUN_SPEC_SCHEMA_VERSION
        ):
            raise ValueError("scenario run spec schema is not frozen")
        _sha(self.permit_sha, "permit_sha")
        _sha(self.application_spec_sha, "application_spec_sha")
        _text(self.scenario_id, "scenario_id")
        _sha(self.scenario_sha, "scenario_sha")
        if self.fejer_order not in T_CANDIDATES:
            raise ValueError("scenario Fejer order is not selected")
        if type(self.source_basis) is not BasisManifest:
            raise TypeError("source_basis has the wrong strict type")
        if type(self.readout_basis) is not BasisManifest:
            raise TypeError("readout_basis has the wrong strict type")
        if (
            self.source_basis.role != "source"
            or self.readout_basis.role != "readout"
            or self.source_basis.state_schema_id
            != self.readout_basis.state_schema_id
            or self.source_basis.channel_order
            != self.readout_basis.channel_order
        ):
            raise ValueError("scenario source/readout interface is inconsistent")
        if type(self.response_grid) is not ResponseKGridManifest:
            raise TypeError("response_grid has the wrong strict type")
        if type(self.source_readout_bridge_grid) is not BridgeKGridManifest:
            raise TypeError("bridge grid has the wrong strict type")
        if (
            type(self.source_readout_bridge_steps) is not tuple
            or not self.source_readout_bridge_steps
        ):
            raise ValueError("source bridge steps must be a non-empty tuple")
        if (
            type(self.reference_reciprocal_index) is not tuple
            or not self.reference_reciprocal_index
        ):
            raise ValueError("reference reciprocal index must be non-empty")
        if (
            type(self.preregistered_phase_bands) is not tuple
            or not self.preregistered_phase_bands
        ):
            raise ValueError("phase bands must be non-empty")
        if type(self.expected_shell_rank) is not int or self.expected_shell_rank <= 0:
            raise ValueError("expected_shell_rank must be positive")
        if type(self.source_trial_vectors) is not FrozenComplexTensor:
            raise TypeError("source_trial_vectors has the wrong strict type")
        source_count = len(self.source_basis.vectors_wire)
        source_trials = frozen_tensor_array(self.source_trial_vectors)
        if (
            source_trials.shape != (source_count, source_count)
            or not np.array_equal(
                source_trials,
                np.eye(source_count, dtype=np.complex128),
            )
        ):
            raise ValueError("source trial vectors are not the frozen identity")
        if self.bridge_tolerance != BRIDGE_TOLERANCE:
            raise ValueError("bridge tolerance is not frozen")
        _sha(self.run_spec_sha, "run_spec_sha")


def application_scenario_run_spec_payload(
    run_spec: ApplicationScenarioRunSpec,
) -> dict[str, object]:
    _exact_record(run_spec, ApplicationScenarioRunSpec, "scenario run spec")
    return _payload_without_hash(run_spec, "run_spec_sha")


@dataclass(frozen=True)
class ApplicationScenarioMaterialization:
    """Raw, recursively hashed C06--C12 scenario construction body."""

    materialization_schema_version: str
    permit: CalibrationApplicationPermit
    scenario_spec: ApplicationScenarioExecutionSpec
    scenario_id: str
    scenario_sha: str
    selected_fejer_order: int
    run_spec: ApplicationScenarioRunSpec
    application_recipe: ApplicationRecipeArtifact
    recipe_sha: str
    construction_trace: ConstructionTrace
    operator_payload: tuple[PrimitiveOperatorWire, ...]
    ablation_pair_snapshot: AblationPairSnapshot
    interface_sha: str
    source_basis_sha: str
    readout_basis_sha: str
    response_grid_sha: str
    bridge_grid_sha: str
    run_spec_sha: str
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    actual_factory_sha: str
    ablated_factory_sha: str
    ablation_manifest_sha: str
    ablation_construction_sha: str
    materialization_sha: str

    def __post_init__(self) -> None:
        if (
            self.materialization_schema_version
            != APPLICATION_SCENARIO_MATERIALIZATION_SCHEMA_VERSION
        ):
            raise ValueError("application materialization schema is not frozen")
        if type(self.permit) is not CalibrationApplicationPermit:
            raise TypeError("materialization permit has the wrong strict type")
        if type(self.scenario_spec) is not ApplicationScenarioExecutionSpec:
            raise TypeError("scenario spec has the wrong strict type")
        if (
            self.scenario_id != self.scenario_spec.scenario_id
            or self.scenario_sha != self.scenario_spec.scenario_sha
        ):
            raise ValueError("scenario ID/SHA summary differs from scenario body")
        if (
            self.scenario_spec.execution_lane != "BLOCK_SUCCESS"
            or self.scenario_spec not in self.permit.application_spec.scenario_execution_specs
        ):
            raise ValueError("materialization scenario is not permit BLOCK_SUCCESS")
        if self.selected_fejer_order != self.permit.selected_fejer_order:
            raise ValueError("materialization Fejer order differs from permit")
        if type(self.run_spec) is not ApplicationScenarioRunSpec:
            raise TypeError("run_spec has the wrong strict type")
        if (
            self.run_spec.permit_sha != self.permit.permit_sha
            or self.run_spec.application_spec_sha
            != self.permit.application_spec.application_spec_sha
            or self.run_spec.scenario_id != self.scenario_id
            or self.run_spec.scenario_sha != self.scenario_sha
            or self.run_spec.fejer_order != self.selected_fejer_order
        ):
            raise ValueError("scenario run spec is not fully materialization-bound")
        if type(self.application_recipe) is not ApplicationRecipeArtifact:
            raise TypeError("application recipe has the wrong strict type")
        recipe = self.application_recipe
        if (
            recipe.scenario_id != self.scenario_id
            or recipe.scenario_sha != self.scenario_sha
            or recipe.application_spec_sha
            != self.permit.application_spec.application_spec_sha
        ):
            raise ValueError("application recipe is not permit/scenario bound")
        expected_recipe_sha = recipe.recipe_sha
        expected_actual_effect = recipe.actual_effect_digest
        expected_ablated_effect = recipe.matched_ablated_effect_digest
        if (
            self.recipe_sha != expected_recipe_sha
            or self.actual_effect_digest != expected_actual_effect
            or self.matched_ablated_effect_digest != expected_ablated_effect
        ):
            raise ValueError("materialization recipe/effect summary mismatch")
        if type(self.construction_trace) is not ConstructionTrace:
            raise TypeError("construction_trace has the wrong strict type")
        if (
            type(self.operator_payload) is not tuple
            or not self.operator_payload
            or not all(
                type(item) is PrimitiveOperatorWire
                for item in self.operator_payload
            )
        ):
            raise TypeError("operator payload has the wrong strict type")
        if len(self.operator_payload) != len(self.construction_trace.primitives):
            raise ValueError("operator and trace primitive counts differ")
        if type(self.ablation_pair_snapshot) is not AblationPairSnapshot:
            raise TypeError("ablation pair snapshot has the wrong strict type")
        for field in (
            "recipe_sha",
            "interface_sha",
            "source_basis_sha",
            "readout_basis_sha",
            "response_grid_sha",
            "bridge_grid_sha",
            "run_spec_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "actual_factory_sha",
            "ablated_factory_sha",
            "ablation_manifest_sha",
            "ablation_construction_sha",
            "materialization_sha",
        ):
            _sha(getattr(self, field), field)
        snapshot = self.ablation_pair_snapshot
        if (
            not snapshot.construction_status.defined
            or self.actual_factory_sha != snapshot.actual_factory.factory_sha
            or self.ablated_factory_sha != snapshot.ablated_factory.factory_sha
            or self.ablation_manifest_sha != snapshot.ablation_manifest.manifest_sha
            or self.ablation_construction_sha != snapshot.ablation_construction_sha
        ):
            raise ValueError("materialization pair summary differs from snapshot")
        if (
            snapshot.actual_factory.construction_trace_sha
            != self.construction_trace.trace_sha
            or snapshot.ablated_factory.construction_trace_sha
            != self.construction_trace.trace_sha
            or snapshot.actual_factory.interface
            != snapshot.ablated_factory.interface
            or self.interface_sha
            != _interface_sha(snapshot.actual_factory.interface)
            or snapshot.actual_factory.source_manifest_id
            != self.source_basis_sha
            or snapshot.ablated_factory.source_manifest_id
            != self.source_basis_sha
            or snapshot.actual_factory.readout_basis
            != self.run_spec.readout_basis
            or snapshot.ablated_factory.readout_basis
            != self.run_spec.readout_basis
        ):
            raise ValueError("materialization trace/interface/basis binding mismatch")
        if (
            self.source_basis_sha != self.run_spec.source_basis.manifest_id
            or self.readout_basis_sha != self.run_spec.readout_basis.manifest_id
            or self.response_grid_sha != self.run_spec.response_grid.response_grid_sha
            or self.bridge_grid_sha
            != self.run_spec.source_readout_bridge_grid.bridge_grid_sha
            or self.run_spec_sha != self.run_spec.run_spec_sha
        ):
            raise ValueError("materialization run-spec SHA summary mismatch")
        conditioned_count = sum(
            primitive.kind is MechanismKind.TARGET_CONDITIONED
            for primitive in self.construction_trace.primitives
        )
        if (
            len(snapshot.ablation_manifest.replacements)
            != conditioned_count
        ):
            raise ValueError("matched replacements differ from conditioned slots")
        if self.actual_effect_digest == self.matched_ablated_effect_digest:
            raise ValueError("actual and matched-ablated effects are identical")


def application_scenario_materialization_payload(
    materialization: ApplicationScenarioMaterialization,
) -> dict[str, object]:
    _exact_record(
        materialization,
        ApplicationScenarioMaterialization,
        "application scenario materialization",
    )
    return _payload_without_hash(materialization, "materialization_sha")


def _derive_scenario_bases(
    state_schema_id: str,
    channel_order: tuple[str, ...],
    source_injection: FrozenComplexTensor,
    readout: FrozenComplexTensor,
) -> tuple[BasisManifest, BasisManifest]:
    source = build_basis_manifest(
        role="source",
        state_schema_id=state_schema_id,
        channel_order=channel_order,
        vectors=frozen_tensor_array(source_injection),
    )
    readout_basis = build_basis_manifest(
        role="readout",
        state_schema_id=state_schema_id,
        channel_order=channel_order,
        vectors=frozen_tensor_array(readout),
    )
    return source, readout_basis


def _expected_scenario_run_spec(
    permit: CalibrationApplicationPermit,
    scenario: ApplicationScenarioExecutionSpec,
    source: BasisManifest,
    readout: BasisManifest,
) -> ApplicationScenarioRunSpec:
    source_count = len(source.vectors_wire)
    provisional = ApplicationScenarioRunSpec(
        run_spec_schema_version=APPLICATION_SCENARIO_RUN_SPEC_SCHEMA_VERSION,
        permit_sha=permit.permit_sha,
        application_spec_sha=permit.application_spec.application_spec_sha,
        scenario_id=scenario.scenario_id,
        scenario_sha=scenario.scenario_sha,
        fejer_order=permit.selected_fejer_order,
        source_basis=source,
        readout_basis=readout,
        response_grid=permit.response_grid,
        source_readout_bridge_grid=permit.source_readout_bridge_grid,
        source_readout_bridge_steps=permit.source_readout_bridge_steps,
        reference_reciprocal_index=permit.reference_reciprocal_index,
        preregistered_phase_bands=permit.preregistered_phase_bands,
        expected_shell_rank=permit.expected_shell_rank,
        source_trial_vectors=freeze_complex_tensor(
            np.eye(source_count, dtype=np.complex128)
        ),
        bridge_tolerance=BRIDGE_TOLERANCE,
        run_spec_sha="0" * 64,
    )
    return replace(
        provisional,
        run_spec_sha=canonical_sha(
            application_scenario_run_spec_payload(provisional)
        ),
    )


def _interface_sha(interface: PrimitiveInterface) -> str:
    return canonical_sha(
        {
            "interface_id": interface.interface_id,
            "state_schema_id": interface.state_schema_id,
            "spatial_ndim": interface.spatial_ndim,
            "channel_order": list(interface.channel_order),
            "dtype": interface.dtype,
            "backend": interface.backend,
        }
    )


def _scenario_from_permit(
    permit: CalibrationApplicationPermit,
    scenario_id: str,
) -> ApplicationScenarioExecutionSpec:
    identifier = _text(scenario_id, "scenario_id")
    if identifier not in _ALLOWED_SCENARIOS:
        raise ValueError("scenario is outside the C06-C12 materializer")
    matches = tuple(
        scenario
        for scenario in permit.application_spec.scenario_execution_specs
        if scenario.scenario_id == identifier
    )
    if len(matches) != 1:
        raise ValueError("scenario is not uniquely bound to this permit")
    scenario = matches[0]
    if (
        scenario.execution_lane != "BLOCK_SUCCESS"
        or scenario.expected_terminal_stage != "success"
        or scenario.expected_undefined_reason is not None
    ):
        raise ValueError("scenario is not a C06-C12 BLOCK_SUCCESS lane")
    return scenario


def _materialize_pair(
    permit_view,
    scenario: ApplicationScenarioExecutionSpec,
    source: BasisManifest,
    readout: BasisManifest,
    trace: ConstructionTrace,
    operators: tuple[PrimitiveOperatorWire, ...],
    interface: PrimitiveInterface,
    carrier_target: FrozenSyntheticTarget,
    carrier_dt: float,
) -> tuple[AblationConstructionOutcome, VerifiedFactory, VerifiedFactory]:
    application = permit_view.permit.application_spec
    actual = build_factory_from_trace(
        trace,
        carrier_target,
        factory_id=f"factory.{scenario.scenario_id}.v1",
        interface=interface,
        state_shape=(len(source.channel_order),)
        + application.grid_protocol.spatial_shape,
        dt=carrier_dt,
        target_blind_parameters=(
            ("selected_fejer_order", float(permit_view.permit.selected_fejer_order)),
        ),
        layer_slot_ids=tuple(item.layer_slot_id for item in operators),
        operator_payload=operators,
        source_manifest_id=source.manifest_id,
        readout_basis=readout,
        boundary_manifest_id="periodic-v1",
    )
    outcome = _verify_construction_outcome(matched_ablation(actual))
    if not outcome.status.defined or outcome.pair is None:
        raise ValueError("application scenario did not form a matched pair")
    return outcome, outcome.pair.actual, outcome.pair.ablated


def _carrier_target_and_dt(
    permit_view,
) -> tuple[FrozenSyntheticTarget, float]:
    calibration_view = _reverify_verified_window_threshold_calibration(
        permit_view.calibration
    )
    registry_view = _reverify_verified_control_registry(calibration_view.registry)
    if registry_view.parent is not permit_view.parent:
        raise ValueError("permit calibration parent identity mismatch")
    carrier = registry_view.controls[0]
    carrier_view = _reverify_verified_factory(carrier.factory)
    return carrier.target, carrier_view.factory.dt


def _expected_application_scenario_materialization(
    permit: VerifiedCalibrationApplicationPermit,
    scenario_id: str,
) -> tuple[
    ApplicationScenarioMaterialization,
    AblationConstructionOutcome,
    VerifiedFactory,
    VerifiedFactory,
]:
    permit_view = _reverify_verified_calibration_application_permit(permit)
    raw_permit = permit_view.permit
    scenario = _scenario_from_permit(raw_permit, scenario_id)
    application_recipe = build_application_recipe(
        permit_view.parent,
        scenario.scenario_id,
    )
    recipe_sha = application_recipe.recipe_sha
    source_tensor = application_recipe.source_injection
    readout_tensor = application_recipe.readout
    actual_effect_digest = application_recipe.actual_effect_digest
    ablated_effect_digest = (
        application_recipe.matched_ablated_effect_digest
    )
    channel_order = application_recipe.channel_order
    state_schema_id = application_recipe.state_schema_id
    source, readout = _derive_scenario_bases(
        state_schema_id,
        channel_order,
        source_tensor,
        readout_tensor,
    )
    if (
        source != raw_permit.source_basis
        or readout != raw_permit.readout_basis
    ):
        raise ValueError("scenario-derived source/readout differ from permit")
    run_spec = _expected_scenario_run_spec(
        raw_permit,
        scenario,
        source,
        readout,
    )
    interface = PrimitiveInterface(
        interface_id=f"interface.{scenario.scenario_id}.v1",
        state_schema_id=state_schema_id,
        spatial_ndim=raw_permit.application_spec.grid_protocol.spatial_ndim,
        channel_order=channel_order,
        dtype="complex128",
        backend="numpy",
    )
    carrier_target, carrier_dt = _carrier_target_and_dt(permit_view)
    target_spec_id = carrier_target.target_spec_id
    trace, operators = build_application_recipe_trace_and_operators(
        permit_view.parent,
        application_recipe,
        target_spec_id=target_spec_id,
        interface=interface,
    )
    outcome, actual, ablated = _materialize_pair(
        permit_view,
        scenario,
        source,
        readout,
        trace,
        operators,
        interface,
        carrier_target,
        carrier_dt,
    )
    snapshot, snapshot_actual, snapshot_ablated = _pair_snapshot(outcome)
    if snapshot_actual is not actual or snapshot_ablated is not ablated:
        raise AssertionError("matched pair identity changed during snapshot")
    provisional = ApplicationScenarioMaterialization(
        materialization_schema_version=(
            APPLICATION_SCENARIO_MATERIALIZATION_SCHEMA_VERSION
        ),
        permit=raw_permit,
        scenario_spec=scenario,
        scenario_id=scenario.scenario_id,
        scenario_sha=scenario.scenario_sha,
        selected_fejer_order=raw_permit.selected_fejer_order,
        run_spec=run_spec,
        application_recipe=application_recipe,
        recipe_sha=recipe_sha,
        construction_trace=trace,
        operator_payload=operators,
        ablation_pair_snapshot=snapshot,
        interface_sha=_interface_sha(interface),
        source_basis_sha=source.manifest_id,
        readout_basis_sha=readout.manifest_id,
        response_grid_sha=raw_permit.response_grid.response_grid_sha,
        bridge_grid_sha=(
            raw_permit.source_readout_bridge_grid.bridge_grid_sha
        ),
        run_spec_sha=run_spec.run_spec_sha,
        actual_effect_digest=actual_effect_digest,
        matched_ablated_effect_digest=ablated_effect_digest,
        actual_factory_sha=snapshot.actual_factory.factory_sha,
        ablated_factory_sha=snapshot.ablated_factory.factory_sha,
        ablation_manifest_sha=snapshot.ablation_manifest.manifest_sha,
        ablation_construction_sha=snapshot.ablation_construction_sha,
        materialization_sha="0" * 64,
    )
    materialization = replace(
        provisional,
        materialization_sha=canonical_sha(
            application_scenario_materialization_payload(provisional)
        ),
    )
    return materialization, outcome, actual, ablated


def _clone_materialization(
    materialization: ApplicationScenarioMaterialization,
) -> ApplicationScenarioMaterialization:
    record_types = (
        *_UPSTREAM_TASK12_WIRE_TYPES,
        *(
            SelectedControlEvidenceRef,
            WindowThresholdSelection,
            WindowThresholdCalibrationManifest,
            CalibrationApplicationPermit,
            ApplicationOperationEffect,
            ApplicationLocalShearStep,
            ApplicationRecipeArtifact,
            ApplicationScenarioRunSpec,
            ConstructionTrace,
            ProvenanceNode,
            CoefficientRecord,
            PrimitiveTrace,
            PrimitiveOperatorWire,
            ApplicationScenarioMaterialization,
        ),
        *_candidate_record_types(
            materialization.permit.calibration_manifest
        ),
    )
    ordered = []
    for record_type in record_types:
        if record_type not in ordered:
            ordered.append(record_type)
    clone = _make_exact_wire_cloner(
        tuple(ordered),
        atomic_types=(
            UndefinedReason,
            ProvenanceOperation,
            MechanismKind,
        ),
    )
    return clone(materialization)  # type: ignore[return-value]


class VerifiedV3M0ApplicationScenarioMaterialization:
    """Opaque live C06--C12 recipe/factory binding, not final evidence."""

    __slots__ = ("__materialization", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        materialization: ApplicationScenarioMaterialization,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("application materialization is module-issued only")
        object.__setattr__(
            self,
            "_VerifiedV3M0ApplicationScenarioMaterialization__materialization",
            materialization,
        )
        object.__setattr__(
            self,
            "_VerifiedV3M0ApplicationScenarioMaterialization__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedV3M0ApplicationScenarioMaterialization__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("application materialization is immutable")

    @property
    def materialization(self) -> ApplicationScenarioMaterialization:
        return _reverify_verified_application_scenario_materialization(
            self
        ).materialization

    @property
    def actual_factory(self) -> VerifiedFactory:
        return _reverify_verified_application_scenario_materialization(
            self
        ).actual

    @property
    def ablated_factory(self) -> VerifiedFactory:
        return _reverify_verified_application_scenario_materialization(
            self
        ).ablated


@dataclass(frozen=True)
class _MaterializationAuthority:
    exposed: ApplicationScenarioMaterialization
    snapshot: ApplicationScenarioMaterialization
    permit: VerifiedCalibrationApplicationPermit
    scenario_id: str
    outcome: AblationConstructionOutcome
    actual: VerifiedFactory
    ablated: VerifiedFactory
    digest: str
    seal: str


@dataclass(frozen=True)
class _ApplicationScenarioMaterializationView:
    materialization: ApplicationScenarioMaterialization
    permit: VerifiedCalibrationApplicationPermit
    outcome: AblationConstructionOutcome
    actual: VerifiedFactory
    ablated: VerifiedFactory


_MATERIALIZATION_LIVE: dict[
    int,
    tuple[
        weakref.ReferenceType[VerifiedV3M0ApplicationScenarioMaterialization],
        _MaterializationAuthority,
    ],
] = {}
_MATERIALIZATION_LOCK = threading.RLock()


def _materialization_seal(
    materialization: ApplicationScenarioMaterialization,
    actual: VerifiedFactory,
    ablated: VerifiedFactory,
) -> str:
    actual_view = _reverify_verified_factory(actual)
    ablated_view = _reverify_verified_factory(ablated)
    if (
        actual_view.factory.factory_sha != materialization.actual_factory_sha
        or ablated_view.factory.factory_sha
        != materialization.ablated_factory_sha
    ):
        raise ValueError("materialization live pair differs from body")
    return canonical_sha(
        {
            "verified_schema_version": (
                "v3m0.verified-application-scenario-materialization.v1"
            ),
            "materialization": {
                **application_scenario_materialization_payload(materialization),
                "materialization_sha": materialization.materialization_sha,
            },
            "live_actual_factory_sha": actual_view.factory.factory_sha,
            "live_ablated_factory_sha": ablated_view.factory.factory_sha,
        }
    )


def _issue_application_scenario_materialization(
    materialization: ApplicationScenarioMaterialization,
    permit: VerifiedCalibrationApplicationPermit,
    outcome: AblationConstructionOutcome,
    actual: VerifiedFactory,
    ablated: VerifiedFactory,
) -> VerifiedV3M0ApplicationScenarioMaterialization:
    exposed = _clone_materialization(materialization)
    snapshot = _clone_materialization(materialization)
    digest = canonical_sha(
        application_scenario_materialization_payload(snapshot)
    )
    if digest != snapshot.materialization_sha:
        raise ValueError("application materialization self-hash mismatch")
    seal = _materialization_seal(snapshot, actual, ablated)
    wrapper = VerifiedV3M0ApplicationScenarioMaterialization(
        _ISSUANCE_TOKEN,
        exposed,
        seal,
    )
    identity = id(wrapper)
    authority = _MaterializationAuthority(
        exposed=exposed,
        snapshot=snapshot,
        permit=permit,
        scenario_id=materialization.scenario_id,
        outcome=outcome,
        actual=actual,
        ablated=ablated,
        digest=digest,
        seal=seal,
    )

    def remove(
        reference: weakref.ReferenceType[
            VerifiedV3M0ApplicationScenarioMaterialization
        ],
        wrapper_id: int = identity,
    ) -> None:
        with _MATERIALIZATION_LOCK:
            current = _MATERIALIZATION_LIVE.get(wrapper_id)
            if current is not None and current[0] is reference:
                del _MATERIALIZATION_LIVE[wrapper_id]

    reference = weakref.ref(wrapper, remove)
    with _MATERIALIZATION_LOCK:
        _MATERIALIZATION_LIVE[identity] = (reference, authority)
    return wrapper


def materialize_v3m0_application_scenario(
    permit: VerifiedCalibrationApplicationPermit,
    scenario_id: str,
) -> VerifiedV3M0ApplicationScenarioMaterialization:
    """Build one live C06--C12 scenario-bound local matched pair."""

    materialization, outcome, actual, ablated = (
        _expected_application_scenario_materialization(
            permit,
            scenario_id,
        )
    )
    return _issue_application_scenario_materialization(
        materialization,
        permit,
        outcome,
        actual,
        ablated,
    )


def verify_v3m0_application_scenario_materialization(
    materialization: ApplicationScenarioMaterialization,
    permit: VerifiedCalibrationApplicationPermit,
    scenario_id: str,
) -> VerifiedV3M0ApplicationScenarioMaterialization:
    """Hydrate only after complete live permit/scenario reconstruction."""

    _preflight_tree(materialization, "raw application materialization")
    _exact_record(
        materialization,
        ApplicationScenarioMaterialization,
        "raw application materialization",
    )
    materialization.__post_init__()
    if materialization.materialization_sha != canonical_sha(
        application_scenario_materialization_payload(materialization)
    ):
        raise ValueError("materialization SHA does not match complete body")
    expected, outcome, actual, ablated = (
        _expected_application_scenario_materialization(
            permit,
            scenario_id,
        )
    )
    if materialization != expected:
        raise ValueError("materialization differs from closed replay")
    return _issue_application_scenario_materialization(
        expected,
        permit,
        outcome,
        actual,
        ablated,
    )


def _reverify_verified_application_scenario_materialization(
    wrapper: VerifiedV3M0ApplicationScenarioMaterialization,
) -> _ApplicationScenarioMaterializationView:
    if type(wrapper) is not VerifiedV3M0ApplicationScenarioMaterialization:
        raise TypeError("runtime requires a live application materialization")
    with _MATERIALIZATION_LOCK:
        current = _MATERIALIZATION_LIVE.get(id(wrapper))
        if current is None or current[0]() is not wrapper:
            raise ValueError("application materialization identity is not live")
        authority = current[1]
    try:
        token = object.__getattribute__(
            wrapper,
            "_VerifiedV3M0ApplicationScenarioMaterialization__token",
        )
        raw = object.__getattribute__(
            wrapper,
            "_VerifiedV3M0ApplicationScenarioMaterialization__materialization",
        )
        seal = object.__getattribute__(
            wrapper,
            "_VerifiedV3M0ApplicationScenarioMaterialization__seal",
        )
    except AttributeError as exc:
        raise ValueError("application materialization is incomplete") from exc
    if token is not _ISSUANCE_TOKEN:
        raise ValueError("application materialization token mismatch")
    expected, _, _, _ = _expected_application_scenario_materialization(
        authority.permit,
        authority.scenario_id,
    )
    observed_digest = canonical_sha(
        application_scenario_materialization_payload(raw)
    )
    snapshot_digest = canonical_sha(
        application_scenario_materialization_payload(authority.snapshot)
    )
    expected_digest = canonical_sha(
        application_scenario_materialization_payload(expected)
    )
    expected_seal = _materialization_seal(
        authority.snapshot,
        authority.actual,
        authority.ablated,
    )
    actual_view = _reverify_verified_factory(authority.actual)
    ablated_view = _reverify_verified_factory(authority.ablated)
    if (
        raw is not authority.exposed
        or raw != authority.snapshot
        or expected != authority.snapshot
        or observed_digest != authority.digest
        or snapshot_digest != authority.digest
        or expected_digest != authority.digest
        or actual_view.factory
        != authority.snapshot.ablation_pair_snapshot.actual_factory
        or ablated_view.factory
        != authority.snapshot.ablation_pair_snapshot.ablated_factory
        or seal != authority.seal
        or seal != expected_seal
    ):
        raise ValueError("application materialization immutable seal mismatch")
    return _ApplicationScenarioMaterializationView(
        materialization=_clone_materialization(authority.snapshot),
        permit=authority.permit,
        outcome=authority.outcome,
        actual=authority.actual,
        ablated=authority.ablated,
    )


__all__ = [
    "APPLICATION_SCENARIO_MATERIALIZATION_SCHEMA_VERSION",
    "APPLICATION_SCENARIO_RUN_SPEC_SCHEMA_VERSION",
    "ApplicationScenarioMaterialization",
    "ApplicationScenarioRunSpec",
    "VerifiedV3M0ApplicationScenarioMaterialization",
    "application_scenario_materialization_payload",
    "application_scenario_run_spec_payload",
    "materialize_v3m0_application_scenario",
    "verify_v3m0_application_scenario_materialization",
]
