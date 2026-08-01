"""Inert C12 local-carrier and per-momentum incidence preflight.

This module closes only the construction question left open by the provisional
Parent candidate.  It compiles the exact C12 candidate scenario to a bounded
real-space canonical-shear carrier, then applies the centered-difference
incidence operator *after* response measurement.  The incidence family never
enters a step or factory payload.  The resulting records are preflight
diagnostics: they issue no permit, response block, or scientific authority.
"""

from __future__ import annotations

import math
import re
from dataclasses import dataclass, replace
from typing import Literal, Optional

import numpy as np
import sympy as sp

from .application_recipes import (
    ApplicationLocalShearStep,
    _executed_effect_digest,
    application_local_shear_step_payload,
)
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    freeze_complex_tensor,
    frozen_tensor_array,
    verify_frozen_tensor,
)
from .frozen_call_graph import freeze_rulespace_call_graph
from .geometry_application_recipes import (
    _common_blind_steps,
    _common_semantic_basis,
    _condition_common_carrier,
    _symbol_from_steps,
)
from .parent_freeze import (
    ParentFreezeCandidateApplication,
    ParentFreezeCandidateManifest,
    ParentFreezeCandidateScenario,
    ScenarioBasisSelectorSpec,
    scenario_basis_selector_spec_payload,
    verify_parent_freeze_candidate,
)
from .response import _extract_projector_candidates, compute_fejer_filtered_response
from .thresholds import BRIDGE_TOLERANCE, RAW_GAP_MIN, T_CANDIDATES


C12_CONTROL_CASE_ID = "C12_NU_INC_IR_NORMALIZATION"
C12_SCENARIO_ID = "v3m0.synthetic-control.c12.v1.scenario.ir-normalization.v1"
C12_FEJER_ORDERS = T_CANDIDATES
C12_RESPONSE_TORUS_DENOMINATOR = 8
C12_RESPONSE_RECIPROCAL_INDICES = ((1,), (2,))
C12_RESPONSE_MOMENTA = (math.pi / 4.0, math.pi / 2.0)
C12_BRANCHES = ("actual", "matched_ablated")
C12_ABSOLUTE_SIGNAL_THRESHOLD = 0.001
C12_PREFLIGHT_STATE = "PREFLIGHT_ONLY_NO_BLOCK_NO_AUTHORITY"
C12_SELECTOR_RANK_REFREEZE_DISPOSITION = "REQUIRES_PARENT_SELECTOR_AND_RANK_REFREEZE"
C12_READOUT_REFREEZE_DISPOSITION = "UNCHANGED_CURRENT_IDENTITY4"
C12_INCIDENCE_FAMILY_ID = "synthetic-lattice-laplacian-incidence-v1"
C12_NORMALIZER_FORMULA_ID = "nu-inc-4-sum-sin2-half-v1"
C12_RECIPE_SCHEMA_VERSION = "v3m0.c12-application-recipe.v1"
C12_INCIDENCE_POINT_SCHEMA_VERSION = "v3m0.c12-incidence-point-wire.v1"
C12_IR_CERTIFICATE_SCHEMA_VERSION = "v3m0.c12-ir-limit-certificate.v1"
C12_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION = (
    "v3m0.c12-analytic-incidence-certificate.v1"
)
C12_NORMALIZER_DERIVATION_ID = (
    "2-exp(+ik)-exp(-ik)-centered-second-difference-v1"
)
C12_IR_LIMIT_FORMULA_ID = (
    "lim-k-to-zero-nu-inc-over-k-squared-equals-one-v1"
)
C12_IR_CONCLUSION = "POSITIVE_SECOND_ORDER_UNIT_CONTINUUM_LIMIT"
C12_ABSOLUTE_SIGNAL_THRESHOLD_AUTHORITY_REF = (
    "WindowThresholdSelection.curv_tau_sig"
)
C12_RAW_BRIDGE_NOISE_EVIDENCE_REF = (
    "SourceReadoutBridgeAudit.curv_operator_error_max"
)
C12_RAW_NOISE_ABSOLUTE_THRESHOLD_AUTHORITY_REF = (
    "rulespace_v3.thresholds.BRIDGE_TOLERANCE"
)
C12_RELATIVE_GAP_THRESHOLD_AUTHORITY_REF = (
    "rulespace_v3.thresholds.RAW_GAP_MIN"
)
C12_STRUCTURE_AUDIT_SCHEMA_VERSION = "v3m0.c12-structure-audit.v1"
C12_BRANCH_POINT_AUDIT_SCHEMA_VERSION = "v3m0.c12-branch-point-audit.v1"
C12_LEGACY_NO_GO_SCHEMA_VERSION = "v3m0.c12-legacy-no-go-audit.v1"
C12_INCIDENCE_PREFLIGHT_SCHEMA_VERSION = "v3m0.c12-incidence-preflight.v1"

_CHANNEL_ORDER = ("q0", "p0", "q1", "p1")
_CHANNEL_INDEX = {name: index for index, name in enumerate(_CHANNEL_ORDER)}
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")
_J = np.asarray(
    (
        (0.0, 1.0, 0.0, 0.0),
        (-1.0, 0.0, 0.0, 0.0),
        (0.0, 0.0, 0.0, 1.0),
        (0.0, 0.0, -1.0, 0.0),
    ),
    dtype=np.complex128,
)


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


def _finite(value: object, field: str, *, nonnegative: bool = False) -> float:
    if type(value) is not float or not math.isfinite(value):
        raise TypeError(f"{field} must be an exact finite fp64 value")
    if nonnegative and value < 0.0:
        raise ValueError(f"{field} must be nonnegative")
    return value


def _exact_record(value: object, record_type: type, field: str) -> None:
    if type(value) is not record_type:
        raise TypeError(f"{field} must be an exact {record_type.__name__}")
    try:
        observed = frozenset(vars(value))
    except TypeError as exc:
        raise TypeError(f"{field} has no exact record body") from exc
    expected = frozenset(record_type.__dataclass_fields__)
    if observed != expected:
        raise ValueError(f"{field} contains missing or unknown fields")


def _finite_spectrum(values: object, field: str, *, length: int) -> None:
    if (
        type(values) is not tuple
        or len(values) != length
        or not all(
            type(value) is float and math.isfinite(value) and value >= 0.0
            for value in values
        )
    ):
        raise TypeError(f"{field} must contain {length} nonnegative fp64 values")


@dataclass(frozen=True)
class C12ApplicationRecipe:
    recipe_schema_version: str
    control_case_id: str
    scenario_id: str
    candidate_sha: str
    candidate_application_sha: str
    candidate_scenario_sha: str
    based_on_application_spec_sha: str
    scenario_sha: str
    based_on_candidate_selector_sha: str
    response_template_sha: str
    candidate_selector_spec: ScenarioBasisSelectorSpec
    candidate_expected_shell_rank: int
    proposed_selector_spec: ScenarioBasisSelectorSpec
    proposed_expected_shell_rank: int
    selector_rank_refreeze_disposition: Literal[
        "REQUIRES_PARENT_SELECTOR_AND_RANK_REFREEZE"
    ]
    readout_refreeze_disposition: Literal["UNCHANGED_CURRENT_IDENTITY4"]
    recipe_id: str
    construction_rule_id: str
    channel_order: tuple[str, ...]
    response_torus_denominator: int
    response_reciprocal_indices: tuple[tuple[int, ...], ...]
    reference_phase_bands: tuple[tuple[float, float], ...]
    primitive_support_radius: int
    semantic_frame_derivation_id: str
    projector_frame_subspace_residual: float
    actual_steps: tuple[ApplicationLocalShearStep, ...]
    matched_ablated_steps: tuple[ApplicationLocalShearStep, ...]
    actual_effect_digest: str
    matched_ablated_effect_digest: str
    incidence_application_stage: Literal["POST_RESPONSE_READOUT_ONLY"]
    uses_global_fft_projection: Literal[False]
    uses_per_k_time_step_projector: Literal[False]
    integration_state: Literal["PREFLIGHT_ONLY_NO_BLOCK_NO_AUTHORITY"]
    recipe_sha: str

    def __post_init__(self) -> None:
        if self.recipe_schema_version != C12_RECIPE_SCHEMA_VERSION:
            raise ValueError("C12 recipe schema is not frozen")
        if self.control_case_id != C12_CONTROL_CASE_ID:
            raise ValueError("C12 recipe control case is not frozen")
        if self.scenario_id != C12_SCENARIO_ID:
            raise ValueError("C12 recipe scenario is not frozen")
        for field in (
            "candidate_sha",
            "candidate_application_sha",
            "candidate_scenario_sha",
            "based_on_application_spec_sha",
            "scenario_sha",
            "based_on_candidate_selector_sha",
            "response_template_sha",
            "actual_effect_digest",
            "matched_ablated_effect_digest",
            "recipe_sha",
        ):
            _sha(getattr(self, field), field)
        _text(self.recipe_id, "recipe_id")
        _text(self.construction_rule_id, "construction_rule_id")
        if type(self.candidate_selector_spec) is not ScenarioBasisSelectorSpec:
            raise TypeError("candidate_selector_spec has the wrong strict type")
        if type(self.proposed_selector_spec) is not ScenarioBasisSelectorSpec:
            raise TypeError("proposed_selector_spec has the wrong strict type")
        if self.candidate_expected_shell_rank != 1:
            raise ValueError("current Parent C12 shell rank is not frozen at one")
        if self.proposed_expected_shell_rank != 2:
            raise ValueError("proposed C12 construction shell rank must be two")
        if (
            self.selector_rank_refreeze_disposition
            != C12_SELECTOR_RANK_REFREEZE_DISPOSITION
        ):
            raise ValueError("C12 selector/rank refreeze disposition is not frozen")
        if self.readout_refreeze_disposition != C12_READOUT_REFREEZE_DISPOSITION:
            raise ValueError("C12 readout refreeze disposition is not frozen")
        if self.channel_order != _CHANNEL_ORDER:
            raise ValueError("C12 channel order is not frozen")
        if self.response_torus_denominator != C12_RESPONSE_TORUS_DENOMINATOR:
            raise ValueError("C12 response denominator is not frozen")
        if self.response_reciprocal_indices != C12_RESPONSE_RECIPROCAL_INDICES:
            raise ValueError("C12 response momenta are not frozen")
        if (
            type(self.reference_phase_bands) is not tuple
            or len(self.reference_phase_bands) != 1
        ):
            raise TypeError("C12 reference phase bands have the wrong shape")
        if self.primitive_support_radius != 1:
            raise ValueError("C12 primitive support radius is not one")
        _text(self.semantic_frame_derivation_id, "semantic_frame_derivation_id")
        _finite(
            self.projector_frame_subspace_residual,
            "projector_frame_subspace_residual",
            nonnegative=True,
        )
        for field in ("actual_steps", "matched_ablated_steps"):
            steps = getattr(self, field)
            if (
                type(steps) is not tuple
                or not steps
                or not all(type(step) is ApplicationLocalShearStep for step in steps)
            ):
                raise TypeError(f"{field} has the wrong strict step type")
        if self.incidence_application_stage != "POST_RESPONSE_READOUT_ONLY":
            raise ValueError("incidence may only be applied after response readout")
        if self.uses_global_fft_projection is not False:
            raise ValueError("global FFT projection is forbidden in the C12 step")
        if self.uses_per_k_time_step_projector is not False:
            raise ValueError("per-k projection is forbidden in the C12 step")
        if self.integration_state != C12_PREFLIGHT_STATE:
            raise ValueError("C12 recipe cannot claim live authority")


@dataclass(frozen=True)
class C12IncidencePointWire:
    point_schema_version: str
    incidence_family_id: str
    normalizer_formula_id: str
    torus_denominator: int
    reciprocal_index: tuple[int, ...]
    momentum: float
    root_of_unity_order: int
    root_of_unity_power: int
    exact_nu_expression: str
    nu_minimal_polynomial_coefficients: tuple[int, ...]
    nu_value: float
    stencil_symbol_residual: float
    incidence_operator: FrozenComplexTensor
    normalized_incidence_operator: FrozenComplexTensor
    application_stage: Literal["POST_RESPONSE_READOUT_ONLY"]
    point_sha: str

    def __post_init__(self) -> None:
        if self.point_schema_version != C12_INCIDENCE_POINT_SCHEMA_VERSION:
            raise ValueError("C12 incidence point schema is not frozen")
        _text(self.incidence_family_id, "incidence_family_id")
        _text(self.normalizer_formula_id, "normalizer_formula_id")
        if type(self.torus_denominator) is not int or self.torus_denominator <= 0:
            raise TypeError("torus_denominator must be a positive exact integer")
        if (
            type(self.reciprocal_index) is not tuple
            or len(self.reciprocal_index) != 1
            or type(self.reciprocal_index[0]) is not int
        ):
            raise TypeError("reciprocal_index must be a one-dimensional integer tuple")
        _finite(self.momentum, "momentum")
        for field in ("root_of_unity_order", "root_of_unity_power"):
            if type(getattr(self, field)) is not int:
                raise TypeError(f"{field} must be an exact integer")
        _text(self.exact_nu_expression, "exact_nu_expression")
        if (
            type(self.nu_minimal_polynomial_coefficients) is not tuple
            or not self.nu_minimal_polynomial_coefficients
            or not all(
                type(value) is int for value in self.nu_minimal_polynomial_coefficients
            )
        ):
            raise TypeError("nu minimal polynomial has the wrong strict type")
        _finite(self.nu_value, "nu_value")
        _finite(
            self.stencil_symbol_residual,
            "stencil_symbol_residual",
            nonnegative=True,
        )
        for field in ("incidence_operator", "normalized_incidence_operator"):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict tensor type")
        if self.application_stage != "POST_RESPONSE_READOUT_ONLY":
            raise ValueError("incidence point is not post-response")
        _sha(self.point_sha, "point_sha")


@dataclass(frozen=True)
class C12IRLimitCertificate:
    certificate_schema_version: str
    incidence_family_id: str
    normalizer_formula_id: str
    symbol_formula_id: str
    stencil_offsets: tuple[tuple[int, ...], ...]
    stencil_coefficients: tuple[int, ...]
    first_brillouin_domain_id: str
    ir_limit_formula_id: str
    ir_limit_order: int
    ir_limit_value: float
    positivity_certified: bool
    point_wires: tuple[C12IncidencePointWire, ...]
    certificate_sha: str

    def __post_init__(self) -> None:
        if self.certificate_schema_version != C12_IR_CERTIFICATE_SCHEMA_VERSION:
            raise ValueError("C12 IR certificate schema is not frozen")
        for field in (
            "incidence_family_id",
            "normalizer_formula_id",
            "symbol_formula_id",
            "first_brillouin_domain_id",
            "ir_limit_formula_id",
        ):
            _text(getattr(self, field), field)
        if type(self.stencil_offsets) is not tuple:
            raise TypeError("stencil_offsets must be a tuple")
        if type(self.stencil_coefficients) is not tuple or not all(
            type(value) is int for value in self.stencil_coefficients
        ):
            raise TypeError("stencil_coefficients must be exact integers")
        if type(self.ir_limit_order) is not int:
            raise TypeError("ir_limit_order must be an exact integer")
        _finite(self.ir_limit_value, "ir_limit_value")
        if type(self.positivity_certified) is not bool:
            raise TypeError("positivity_certified must be an exact bool")
        if type(self.point_wires) is not tuple or not all(
            type(point) is C12IncidencePointWire for point in self.point_wires
        ):
            raise TypeError("point_wires have the wrong strict type")
        _sha(self.certificate_sha, "certificate_sha")


@dataclass(frozen=True)
class C12AnalyticIncidenceCertificate:
    """Authority-neutral exact certificate for the C12 incidence family."""

    certificate_schema_version: str
    incidence_family_id: str
    normalizer_formula_id: str
    normalizer_derivation_id: str
    stencil_offsets: tuple[tuple[int, ...], ...]
    stencil_coefficients: tuple[int, ...]
    first_brillouin_domain_id: str
    ir_limit_formula_id: str
    ir_limit_order: int
    ir_limit_value: float
    ir_conclusion: str
    positivity_certified: bool
    absolute_signal_threshold_authority_ref: str
    raw_bridge_noise_evidence_ref: str
    raw_noise_absolute_threshold_authority_ref: str
    relative_gap_threshold_authority_ref: str
    point_wires: tuple[C12IncidencePointWire, ...]
    certificate_sha: str

    def __post_init__(self) -> None:
        if (
            self.certificate_schema_version
            != C12_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION
        ):
            raise ValueError("C12 analytic incidence certificate schema drifted")
        for field in (
            "incidence_family_id",
            "normalizer_formula_id",
            "normalizer_derivation_id",
            "first_brillouin_domain_id",
            "ir_limit_formula_id",
            "ir_conclusion",
            "absolute_signal_threshold_authority_ref",
            "raw_bridge_noise_evidence_ref",
            "raw_noise_absolute_threshold_authority_ref",
            "relative_gap_threshold_authority_ref",
        ):
            _text(getattr(self, field), field)
        if (
            type(self.stencil_offsets) is not tuple
            or not all(
                type(offset) is tuple
                and all(type(value) is int for value in offset)
                for offset in self.stencil_offsets
            )
        ):
            raise TypeError("stencil_offsets must contain exact integer tuples")
        if type(self.stencil_coefficients) is not tuple or not all(
            type(value) is int for value in self.stencil_coefficients
        ):
            raise TypeError("stencil_coefficients must be exact integers")
        if type(self.ir_limit_order) is not int:
            raise TypeError("ir_limit_order must be an exact integer")
        _finite(self.ir_limit_value, "ir_limit_value")
        if type(self.positivity_certified) is not bool:
            raise TypeError("positivity_certified must be an exact bool")
        if type(self.point_wires) is not tuple or not all(
            type(point) is C12IncidencePointWire for point in self.point_wires
        ):
            raise TypeError("point_wires have the wrong strict type")
        _sha(self.certificate_sha, "certificate_sha")


@dataclass(frozen=True)
class C12StructureAudit:
    audit_schema_version: str
    recipe_sha: str
    branch: Literal["actual", "matched_ablated"]
    lattice_size: int
    primitive_support_offsets: tuple[tuple[int, ...], ...]
    composite_support_radius: int
    max_bridge_error: float
    max_unitary_error: float
    max_symplectic_error: float
    max_reality_error: float
    audit_sha: str

    def __post_init__(self) -> None:
        if self.audit_schema_version != C12_STRUCTURE_AUDIT_SCHEMA_VERSION:
            raise ValueError("C12 structure audit schema is not frozen")
        _sha(self.recipe_sha, "recipe_sha")
        _text(self.branch, "branch")
        if type(self.lattice_size) is not int or self.lattice_size <= 0:
            raise TypeError("lattice_size must be a positive exact integer")
        if type(self.primitive_support_offsets) is not tuple:
            raise TypeError("primitive_support_offsets must be a tuple")
        if type(self.composite_support_radius) is not int:
            raise TypeError("composite_support_radius must be an exact integer")
        for field in (
            "max_bridge_error",
            "max_unitary_error",
            "max_symplectic_error",
            "max_reality_error",
        ):
            _finite(getattr(self, field), field, nonnegative=True)
        _sha(self.audit_sha, "audit_sha")


@dataclass(frozen=True)
class C12BranchPointAudit:
    audit_schema_version: str
    recipe_sha: str
    point_sha: str
    selected_fejer_order: int
    branch: Literal["actual", "matched_ablated"]
    reciprocal_index: tuple[int, ...]
    momentum: float
    shell_phase: float
    endpoint_shell_rank: int
    endpoint_participation: float
    nu_value: float
    raw_response: FrozenComplexTensor
    normalized_response: FrozenComplexTensor
    raw_singular_values: tuple[float, ...]
    normalized_singular_values: tuple[float, ...]
    raw_rank: int
    normalized_rank: int
    raw_active_min: float
    normalized_active_min: float
    raw_inactive_max: Optional[float]
    normalized_inactive_max: Optional[float]
    raw_bridge_noise: float
    normalized_bridge_noise: float
    absolute_signal_margin: float
    raw_bridge_noise_margin: float
    relative_gap: float
    relative_gap_margin: float
    audit_sha: str

    def __post_init__(self) -> None:
        if self.audit_schema_version != C12_BRANCH_POINT_AUDIT_SCHEMA_VERSION:
            raise ValueError("C12 point audit schema is not frozen")
        _sha(self.recipe_sha, "recipe_sha")
        _sha(self.point_sha, "point_sha")
        if self.selected_fejer_order not in C12_FEJER_ORDERS:
            raise ValueError("C12 point audit Fejer order is not preregistered")
        _text(self.branch, "branch")
        if type(self.reciprocal_index) is not tuple:
            raise TypeError("reciprocal_index must be a tuple")
        for field in (
            "momentum",
            "shell_phase",
            "endpoint_participation",
            "nu_value",
            "raw_active_min",
            "normalized_active_min",
            "raw_bridge_noise",
            "normalized_bridge_noise",
            "absolute_signal_margin",
            "raw_bridge_noise_margin",
            "relative_gap",
            "relative_gap_margin",
        ):
            _finite(getattr(self, field), field)
        for field in ("endpoint_shell_rank", "raw_rank", "normalized_rank"):
            if type(getattr(self, field)) is not int:
                raise TypeError(f"{field} must be an exact integer")
        for field in ("raw_response", "normalized_response"):
            if type(getattr(self, field)) is not FrozenComplexTensor:
                raise TypeError(f"{field} has the wrong strict tensor type")
        _finite_spectrum(self.raw_singular_values, "raw_singular_values", length=2)
        _finite_spectrum(
            self.normalized_singular_values,
            "normalized_singular_values",
            length=2,
        )
        for field in ("raw_inactive_max", "normalized_inactive_max"):
            value = getattr(self, field)
            if value is not None:
                _finite(value, field, nonnegative=True)
        _sha(self.audit_sha, "audit_sha")


@dataclass(frozen=True)
class C12LegacyNoGoAudit:
    audit_schema_version: str
    recipe_sha: str
    legacy_source_id: str
    legacy_declared_shell_rank: int
    selected_fejer_order: int
    reciprocal_index: tuple[int, ...]
    singular_values: tuple[float, ...]
    observed_rank: int
    off_band_active_min: float
    absolute_signal_threshold: float
    conclusion: Literal["REJECT_IDENTITY4_AND_RANK1"]
    audit_sha: str

    def __post_init__(self) -> None:
        if self.audit_schema_version != C12_LEGACY_NO_GO_SCHEMA_VERSION:
            raise ValueError("C12 legacy no-go schema is not frozen")
        _sha(self.recipe_sha, "recipe_sha")
        _text(self.legacy_source_id, "legacy_source_id")
        for field in (
            "legacy_declared_shell_rank",
            "selected_fejer_order",
            "observed_rank",
        ):
            if type(getattr(self, field)) is not int:
                raise TypeError(f"{field} must be an exact integer")
        if type(self.reciprocal_index) is not tuple:
            raise TypeError("reciprocal_index must be a tuple")
        _finite_spectrum(self.singular_values, "singular_values", length=4)
        _finite(self.off_band_active_min, "off_band_active_min", nonnegative=True)
        _finite(
            self.absolute_signal_threshold,
            "absolute_signal_threshold",
            nonnegative=True,
        )
        if self.conclusion != "REJECT_IDENTITY4_AND_RANK1":
            raise ValueError("legacy no-go conclusion is not frozen")
        _sha(self.audit_sha, "audit_sha")


@dataclass(frozen=True)
class C12IncidencePreflight:
    preflight_schema_version: str
    candidate_sha: str
    candidate_application_sha: str
    candidate_scenario_sha: str
    scenario_id: str
    recipe: C12ApplicationRecipe
    ir_certificate: C12IRLimitCertificate
    structure_audits: tuple[C12StructureAudit, ...]
    point_audits: tuple[C12BranchPointAudit, ...]
    legacy_no_go_audit: C12LegacyNoGoAudit
    expected_curvature_mode_count: int
    absolute_signal_threshold: float
    raw_noise_absolute_threshold: float
    relative_gap_threshold: float
    integration_state: Literal["PREFLIGHT_ONLY_NO_BLOCK_NO_AUTHORITY"]
    preflight_sha: str

    def __post_init__(self) -> None:
        if self.preflight_schema_version != C12_INCIDENCE_PREFLIGHT_SCHEMA_VERSION:
            raise ValueError("C12 preflight schema is not frozen")
        for field in (
            "candidate_sha",
            "candidate_application_sha",
            "candidate_scenario_sha",
            "preflight_sha",
        ):
            _sha(getattr(self, field), field)
        if self.scenario_id != C12_SCENARIO_ID:
            raise ValueError("C12 preflight scenario is not frozen")
        if type(self.recipe) is not C12ApplicationRecipe:
            raise TypeError("recipe has the wrong strict type")
        if type(self.ir_certificate) is not C12IRLimitCertificate:
            raise TypeError("ir_certificate has the wrong strict type")
        if type(self.structure_audits) is not tuple or not all(
            type(item) is C12StructureAudit for item in self.structure_audits
        ):
            raise TypeError("structure_audits have the wrong strict type")
        if type(self.point_audits) is not tuple or not all(
            type(item) is C12BranchPointAudit for item in self.point_audits
        ):
            raise TypeError("point_audits have the wrong strict type")
        if type(self.legacy_no_go_audit) is not C12LegacyNoGoAudit:
            raise TypeError("legacy_no_go_audit has the wrong strict type")
        if self.expected_curvature_mode_count != 2:
            raise ValueError("C12 curvature mode count is not two")
        for field in (
            "absolute_signal_threshold",
            "raw_noise_absolute_threshold",
            "relative_gap_threshold",
        ):
            _finite(getattr(self, field), field, nonnegative=True)
        if self.integration_state != C12_PREFLIGHT_STATE:
            raise ValueError("C12 preflight cannot claim authority")


def _step_record(step: ApplicationLocalShearStep) -> dict[str, object]:
    return {
        **application_local_shear_step_payload(step),
        "step_sha": step.step_sha,
    }


def c12_application_recipe_payload(recipe: C12ApplicationRecipe) -> dict[str, object]:
    if type(recipe) is not C12ApplicationRecipe:
        raise TypeError("recipe must be an exact C12ApplicationRecipe")
    return {
        "recipe_schema_version": recipe.recipe_schema_version,
        "control_case_id": recipe.control_case_id,
        "scenario_id": recipe.scenario_id,
        "candidate_sha": recipe.candidate_sha,
        "candidate_application_sha": recipe.candidate_application_sha,
        "candidate_scenario_sha": recipe.candidate_scenario_sha,
        "based_on_application_spec_sha": recipe.based_on_application_spec_sha,
        "scenario_sha": recipe.scenario_sha,
        "based_on_candidate_selector_sha": (recipe.based_on_candidate_selector_sha),
        "response_template_sha": recipe.response_template_sha,
        "candidate_selector_spec": {
            **scenario_basis_selector_spec_payload(recipe.candidate_selector_spec),
            "selector_sha": recipe.candidate_selector_spec.selector_sha,
        },
        "candidate_expected_shell_rank": recipe.candidate_expected_shell_rank,
        "proposed_selector_spec": {
            **scenario_basis_selector_spec_payload(recipe.proposed_selector_spec),
            "selector_sha": recipe.proposed_selector_spec.selector_sha,
        },
        "proposed_expected_shell_rank": recipe.proposed_expected_shell_rank,
        "selector_rank_refreeze_disposition": (
            recipe.selector_rank_refreeze_disposition
        ),
        "readout_refreeze_disposition": recipe.readout_refreeze_disposition,
        "recipe_id": recipe.recipe_id,
        "construction_rule_id": recipe.construction_rule_id,
        "channel_order": list(recipe.channel_order),
        "response_torus_denominator": recipe.response_torus_denominator,
        "response_reciprocal_indices": [
            list(item) for item in recipe.response_reciprocal_indices
        ],
        "reference_phase_bands": [list(item) for item in recipe.reference_phase_bands],
        "primitive_support_radius": recipe.primitive_support_radius,
        "semantic_frame_derivation_id": recipe.semantic_frame_derivation_id,
        "projector_frame_subspace_residual": (recipe.projector_frame_subspace_residual),
        "actual_steps": [_step_record(step) for step in recipe.actual_steps],
        "matched_ablated_steps": [
            _step_record(step) for step in recipe.matched_ablated_steps
        ],
        "actual_effect_digest": recipe.actual_effect_digest,
        "matched_ablated_effect_digest": recipe.matched_ablated_effect_digest,
        "incidence_application_stage": recipe.incidence_application_stage,
        "uses_global_fft_projection": recipe.uses_global_fft_projection,
        "uses_per_k_time_step_projector": recipe.uses_per_k_time_step_projector,
        "integration_state": recipe.integration_state,
    }


def c12_incidence_point_wire_payload(
    point: C12IncidencePointWire,
) -> dict[str, object]:
    if type(point) is not C12IncidencePointWire:
        raise TypeError("point must be an exact C12IncidencePointWire")
    return {
        "point_schema_version": point.point_schema_version,
        "incidence_family_id": point.incidence_family_id,
        "normalizer_formula_id": point.normalizer_formula_id,
        "torus_denominator": point.torus_denominator,
        "reciprocal_index": list(point.reciprocal_index),
        "momentum": point.momentum,
        "root_of_unity_order": point.root_of_unity_order,
        "root_of_unity_power": point.root_of_unity_power,
        "exact_nu_expression": point.exact_nu_expression,
        "nu_minimal_polynomial_coefficients": list(
            point.nu_minimal_polynomial_coefficients
        ),
        "nu_value": point.nu_value,
        "stencil_symbol_residual": point.stencil_symbol_residual,
        "incidence_operator_sha": point.incidence_operator.tensor_sha,
        "normalized_incidence_operator_sha": (
            point.normalized_incidence_operator.tensor_sha
        ),
        "application_stage": point.application_stage,
    }


def _point_record(point: C12IncidencePointWire) -> dict[str, object]:
    return {**c12_incidence_point_wire_payload(point), "point_sha": point.point_sha}


def c12_ir_limit_certificate_payload(
    certificate: C12IRLimitCertificate,
) -> dict[str, object]:
    if type(certificate) is not C12IRLimitCertificate:
        raise TypeError("certificate must be an exact C12IRLimitCertificate")
    return {
        "certificate_schema_version": certificate.certificate_schema_version,
        "incidence_family_id": certificate.incidence_family_id,
        "normalizer_formula_id": certificate.normalizer_formula_id,
        "symbol_formula_id": certificate.symbol_formula_id,
        "stencil_offsets": [list(item) for item in certificate.stencil_offsets],
        "stencil_coefficients": list(certificate.stencil_coefficients),
        "first_brillouin_domain_id": certificate.first_brillouin_domain_id,
        "ir_limit_formula_id": certificate.ir_limit_formula_id,
        "ir_limit_order": certificate.ir_limit_order,
        "ir_limit_value": certificate.ir_limit_value,
        "positivity_certified": certificate.positivity_certified,
        "point_wires": [_point_record(point) for point in certificate.point_wires],
    }


def c12_analytic_incidence_certificate_payload(
    certificate: C12AnalyticIncidenceCertificate,
) -> dict[str, object]:
    """Return the complete hash body of an analytic-only C12 certificate."""

    _exact_record(
        certificate,
        C12AnalyticIncidenceCertificate,
        "C12 analytic incidence certificate",
    )
    return {
        "certificate_schema_version": certificate.certificate_schema_version,
        "incidence_family_id": certificate.incidence_family_id,
        "normalizer_formula_id": certificate.normalizer_formula_id,
        "normalizer_derivation_id": certificate.normalizer_derivation_id,
        "stencil_offsets": [list(item) for item in certificate.stencil_offsets],
        "stencil_coefficients": list(certificate.stencil_coefficients),
        "first_brillouin_domain_id": certificate.first_brillouin_domain_id,
        "ir_limit_formula_id": certificate.ir_limit_formula_id,
        "ir_limit_order": certificate.ir_limit_order,
        "ir_limit_value": certificate.ir_limit_value,
        "ir_conclusion": certificate.ir_conclusion,
        "positivity_certified": certificate.positivity_certified,
        "absolute_signal_threshold_authority_ref": (
            certificate.absolute_signal_threshold_authority_ref
        ),
        "raw_bridge_noise_evidence_ref": (
            certificate.raw_bridge_noise_evidence_ref
        ),
        "raw_noise_absolute_threshold_authority_ref": (
            certificate.raw_noise_absolute_threshold_authority_ref
        ),
        "relative_gap_threshold_authority_ref": (
            certificate.relative_gap_threshold_authority_ref
        ),
        "point_wires": [_point_record(point) for point in certificate.point_wires],
    }


def c12_structure_audit_payload(audit: C12StructureAudit) -> dict[str, object]:
    if type(audit) is not C12StructureAudit:
        raise TypeError("audit must be an exact C12StructureAudit")
    return {
        "audit_schema_version": audit.audit_schema_version,
        "recipe_sha": audit.recipe_sha,
        "branch": audit.branch,
        "lattice_size": audit.lattice_size,
        "primitive_support_offsets": [
            list(item) for item in audit.primitive_support_offsets
        ],
        "composite_support_radius": audit.composite_support_radius,
        "max_bridge_error": audit.max_bridge_error,
        "max_unitary_error": audit.max_unitary_error,
        "max_symplectic_error": audit.max_symplectic_error,
        "max_reality_error": audit.max_reality_error,
    }


def c12_branch_point_audit_payload(
    audit: C12BranchPointAudit,
) -> dict[str, object]:
    if type(audit) is not C12BranchPointAudit:
        raise TypeError("audit must be an exact C12BranchPointAudit")
    return {
        "audit_schema_version": audit.audit_schema_version,
        "recipe_sha": audit.recipe_sha,
        "point_sha": audit.point_sha,
        "selected_fejer_order": audit.selected_fejer_order,
        "branch": audit.branch,
        "reciprocal_index": list(audit.reciprocal_index),
        "momentum": audit.momentum,
        "shell_phase": audit.shell_phase,
        "endpoint_shell_rank": audit.endpoint_shell_rank,
        "endpoint_participation": audit.endpoint_participation,
        "nu_value": audit.nu_value,
        "raw_response_sha": audit.raw_response.tensor_sha,
        "normalized_response_sha": audit.normalized_response.tensor_sha,
        "raw_singular_values": list(audit.raw_singular_values),
        "normalized_singular_values": list(audit.normalized_singular_values),
        "raw_rank": audit.raw_rank,
        "normalized_rank": audit.normalized_rank,
        "raw_active_min": audit.raw_active_min,
        "normalized_active_min": audit.normalized_active_min,
        "raw_inactive_max": audit.raw_inactive_max,
        "normalized_inactive_max": audit.normalized_inactive_max,
        "raw_bridge_noise": audit.raw_bridge_noise,
        "normalized_bridge_noise": audit.normalized_bridge_noise,
        "absolute_signal_margin": audit.absolute_signal_margin,
        "raw_bridge_noise_margin": audit.raw_bridge_noise_margin,
        "relative_gap": audit.relative_gap,
        "relative_gap_margin": audit.relative_gap_margin,
    }


def c12_legacy_no_go_audit_payload(
    audit: C12LegacyNoGoAudit,
) -> dict[str, object]:
    if type(audit) is not C12LegacyNoGoAudit:
        raise TypeError("audit must be an exact C12LegacyNoGoAudit")
    return {
        "audit_schema_version": audit.audit_schema_version,
        "recipe_sha": audit.recipe_sha,
        "legacy_source_id": audit.legacy_source_id,
        "legacy_declared_shell_rank": audit.legacy_declared_shell_rank,
        "selected_fejer_order": audit.selected_fejer_order,
        "reciprocal_index": list(audit.reciprocal_index),
        "singular_values": list(audit.singular_values),
        "observed_rank": audit.observed_rank,
        "off_band_active_min": audit.off_band_active_min,
        "absolute_signal_threshold": audit.absolute_signal_threshold,
        "conclusion": audit.conclusion,
    }


def c12_incidence_preflight_payload(
    preflight: C12IncidencePreflight,
) -> dict[str, object]:
    if type(preflight) is not C12IncidencePreflight:
        raise TypeError("preflight must be an exact C12IncidencePreflight")
    return {
        "preflight_schema_version": preflight.preflight_schema_version,
        "candidate_sha": preflight.candidate_sha,
        "candidate_application_sha": preflight.candidate_application_sha,
        "candidate_scenario_sha": preflight.candidate_scenario_sha,
        "scenario_id": preflight.scenario_id,
        "recipe": {
            **c12_application_recipe_payload(preflight.recipe),
            "recipe_sha": preflight.recipe.recipe_sha,
        },
        "ir_certificate": {
            **c12_ir_limit_certificate_payload(preflight.ir_certificate),
            "certificate_sha": preflight.ir_certificate.certificate_sha,
        },
        "structure_audits": [
            {**c12_structure_audit_payload(item), "audit_sha": item.audit_sha}
            for item in preflight.structure_audits
        ],
        "point_audits": [
            {**c12_branch_point_audit_payload(item), "audit_sha": item.audit_sha}
            for item in preflight.point_audits
        ],
        "legacy_no_go_audit": {
            **c12_legacy_no_go_audit_payload(preflight.legacy_no_go_audit),
            "audit_sha": preflight.legacy_no_go_audit.audit_sha,
        },
        "expected_curvature_mode_count": preflight.expected_curvature_mode_count,
        "absolute_signal_threshold": preflight.absolute_signal_threshold,
        "raw_noise_absolute_threshold": (preflight.raw_noise_absolute_threshold),
        "relative_gap_threshold": preflight.relative_gap_threshold,
        "integration_state": preflight.integration_state,
    }


def _find_c12_candidate(
    candidate: ParentFreezeCandidateManifest,
) -> tuple[ParentFreezeCandidateApplication, ParentFreezeCandidateScenario]:
    verified = verify_parent_freeze_candidate(candidate)
    applications = tuple(
        item
        for item in verified.application_candidates
        if item.control_case_id == C12_CONTROL_CASE_ID
    )
    if len(applications) != 1:
        raise ValueError(
            "Parent candidate does not contain exactly one C12 application"
        )
    application = applications[0]
    scenarios = tuple(
        item
        for item in application.scenario_candidates
        if item.scenario_execution_spec.scenario_id == C12_SCENARIO_ID
    )
    if len(scenarios) != 1 or len(application.scenario_candidates) != 1:
        raise ValueError("Parent candidate does not contain the unique C12 scenario")
    scenario = scenarios[0]
    execution = scenario.scenario_execution_spec
    template = scenario.response_template
    profile = scenario.prediction_profile
    if (
        execution.execution_lane != "BLOCK_SUCCESS"
        or execution.execution_recipe_id != "two-mode-ir-normalization-v1"
        or execution.expected_terminal_stage != "success"
        or template.construction_preflight_state != "PENDING_CONSTRUCTION_PREFLIGHT"
        or profile.prediction_state != "PENDING_CONSTRUCTION_PREFLIGHT"
        or profile.quantities != ()
        or template.response_torus_denominators != (8,)
        or template.response_reciprocal_indices != C12_RESPONSE_RECIPROCAL_INDICES
        or template.expected_actual_shell_rank != 1
        or template.curvature_incidence_family_id != C12_INCIDENCE_FAMILY_ID
        or template.curvature_normalizer_formula_id != C12_NORMALIZER_FORMULA_ID
    ):
        raise ValueError("Parent candidate C12 scenario contract is not frozen")
    return application, scenario


def _snapshot_selector(
    selector: ScenarioBasisSelectorSpec,
) -> ScenarioBasisSelectorSpec:
    """Detach an exact selector body from the caller-owned Parent candidate."""

    return replace(
        selector,
        source_selector=freeze_complex_tensor(
            frozen_tensor_array(selector.source_selector)
        ),
        readout_selector=freeze_complex_tensor(
            frozen_tensor_array(selector.readout_selector)
        ),
        source_injection=freeze_complex_tensor(
            frozen_tensor_array(selector.source_injection)
        ),
        readout_coisometry=freeze_complex_tensor(
            frozen_tensor_array(selector.readout_coisometry)
        ),
    )


def _closed_common_semantic_frame() -> np.ndarray:
    """Return the C15/C12 shared closed-form semantic frame."""

    root_two = math.sqrt(2.0)
    half_root_two = 1.0 / (2.0 * root_two)
    return np.asarray(
        (
            (1.0 / root_two, 0.0, 1.0 / root_two, 0.0),
            (
                -1.0j * half_root_two,
                -0.5 + 1.0j * half_root_two,
                1.0j * half_root_two,
                0.5 - 1.0j * half_root_two,
            ),
            (0.0, 1.0 / root_two, 0.0, 1.0 / root_two),
            (
                0.5 + 1.0j * half_root_two,
                1.0j * half_root_two,
                -0.5 - 1.0j * half_root_two,
                -1.0j * half_root_two,
            ),
        ),
        dtype=np.complex128,
    )


def _build_proposed_selector(
    candidate_selector: ScenarioBasisSelectorSpec,
    proposed_source: np.ndarray,
) -> ScenarioBasisSelectorSpec:
    candidate_source = frozen_tensor_array(candidate_selector.source_injection)
    candidate_source_selector = frozen_tensor_array(candidate_selector.source_selector)
    candidate_readout_selector = frozen_tensor_array(
        candidate_selector.readout_selector
    )
    candidate_readout = frozen_tensor_array(candidate_selector.readout_coisometry)
    identity = np.eye(4, dtype=np.complex128)
    if (
        candidate_source.shape != (4, 4)
        or candidate_readout.shape != (4, 4)
        or not np.array_equal(candidate_source_selector, identity)
        or not np.array_equal(candidate_readout_selector, identity)
        or not np.array_equal(candidate_source, identity)
        or not np.array_equal(candidate_readout, identity)
    ):
        raise ValueError("current Parent C12 selector is not the frozen identity4 body")
    source_selector = candidate_source.conj().T @ proposed_source
    source_injection = candidate_source @ source_selector
    provisional = ScenarioBasisSelectorSpec(
        selector_schema_version=candidate_selector.selector_schema_version,
        scenario_id=candidate_selector.scenario_id,
        public_source_basis_manifest_id=(
            candidate_selector.public_source_basis_manifest_id
        ),
        public_readout_basis_manifest_id=(
            candidate_selector.public_readout_basis_manifest_id
        ),
        source_selector_derivation_id=(
            "analytic-common-geometry-semantic-frame-first-two-columns-v1"
        ),
        readout_selector_derivation_id=(
            "c12-inherit-current-parent-identity4-readout-v1"
        ),
        source_selector=freeze_complex_tensor(source_selector),
        readout_selector=freeze_complex_tensor(candidate_readout_selector),
        source_injection=freeze_complex_tensor(source_injection),
        readout_coisometry=freeze_complex_tensor(candidate_readout),
        selector_sha="0" * 64,
    )
    return replace(
        provisional,
        selector_sha=canonical_sha(scenario_basis_selector_spec_payload(provisional)),
    )


def _build_recipe(
    candidate: ParentFreezeCandidateManifest,
    application: ParentFreezeCandidateApplication,
    scenario: ParentFreezeCandidateScenario,
) -> C12ApplicationRecipe:
    derivation_digest = scenario.candidate_scenario_sha
    matched_steps = _common_blind_steps(derivation_digest)
    actual_steps = _condition_common_carrier(matched_steps, derivation_digest)
    source = _closed_common_semantic_frame()[:, :2]
    projector_frame = _common_semantic_basis(matched_steps)[:, :2]
    projector_frame_subspace_residual = float(
        np.linalg.norm(
            projector_frame @ projector_frame.conj().T - source @ source.conj().T,
            ord=2,
        )
    )
    candidate_selector = _snapshot_selector(scenario.selector_spec)
    proposed_selector = _build_proposed_selector(candidate_selector, source)
    provisional = C12ApplicationRecipe(
        recipe_schema_version=C12_RECIPE_SCHEMA_VERSION,
        control_case_id=C12_CONTROL_CASE_ID,
        scenario_id=C12_SCENARIO_ID,
        candidate_sha=candidate.candidate_sha,
        candidate_application_sha=application.candidate_application_sha,
        candidate_scenario_sha=scenario.candidate_scenario_sha,
        based_on_application_spec_sha=scenario.based_on_application_spec_sha,
        scenario_sha=scenario.scenario_execution_spec.scenario_sha,
        based_on_candidate_selector_sha=scenario.selector_spec.selector_sha,
        response_template_sha=scenario.response_template.template_sha,
        candidate_selector_spec=candidate_selector,
        candidate_expected_shell_rank=(
            scenario.response_template.expected_actual_shell_rank
        ),
        proposed_selector_spec=proposed_selector,
        proposed_expected_shell_rank=2,
        selector_rank_refreeze_disposition=(C12_SELECTOR_RANK_REFREEZE_DISPOSITION),
        readout_refreeze_disposition=C12_READOUT_REFREEZE_DISPOSITION,
        recipe_id=scenario.scenario_execution_spec.execution_recipe_id,
        construction_rule_id="c12-rank-two-local-incidence-carrier-v1",
        channel_order=_CHANNEL_ORDER,
        response_torus_denominator=C12_RESPONSE_TORUS_DENOMINATOR,
        response_reciprocal_indices=C12_RESPONSE_RECIPROCAL_INDICES,
        reference_phase_bands=scenario.response_template.preregistered_phase_bands,
        primitive_support_radius=1,
        semantic_frame_derivation_id=("analytic-common-geometry-semantic-frame-v1"),
        projector_frame_subspace_residual=projector_frame_subspace_residual,
        actual_steps=actual_steps,
        matched_ablated_steps=matched_steps,
        actual_effect_digest=_executed_effect_digest(actual_steps, "actual"),
        matched_ablated_effect_digest=_executed_effect_digest(
            actual_steps,
            "matched_ablated",
        ),
        incidence_application_stage="POST_RESPONSE_READOUT_ONLY",
        uses_global_fft_projection=False,
        uses_per_k_time_step_projector=False,
        integration_state=C12_PREFLIGHT_STATE,
        recipe_sha="0" * 64,
    )
    result = replace(
        provisional,
        recipe_sha=canonical_sha(c12_application_recipe_payload(provisional)),
    )
    _validate_recipe(result)
    return result


def _validate_step(step: ApplicationLocalShearStep) -> None:
    _exact_record(step, ApplicationLocalShearStep, "C12 local shear step")
    step.__post_init__()
    if step.step_sha != canonical_sha(application_local_shear_step_payload(step)):
        raise ValueError("C12 local shear step SHA does not replay")
    serialized_keys = frozenset(application_local_shear_step_payload(step))
    if any(
        forbidden in key.lower()
        for key in serialized_keys
        for forbidden in ("incidence", "normalizer", "fft", "projector")
    ):
        raise ValueError("C12 incidence leaked into a local step payload")


def _validate_selector_spec(selector: ScenarioBasisSelectorSpec, field: str) -> None:
    _exact_record(selector, ScenarioBasisSelectorSpec, field)
    selector.__post_init__()
    for tensor_field in (
        "source_selector",
        "readout_selector",
        "source_injection",
        "readout_coisometry",
    ):
        tensor = getattr(selector, tensor_field)
        _exact_record(tensor, FrozenComplexTensor, f"{field}.{tensor_field}")
        verify_frozen_tensor(tensor)
    if selector.selector_sha != canonical_sha(
        scenario_basis_selector_spec_payload(selector)
    ):
        raise ValueError(f"{field} SHA does not match its complete body")


def _validate_recipe(recipe: C12ApplicationRecipe) -> None:
    _exact_record(recipe, C12ApplicationRecipe, "C12 recipe")
    recipe.__post_init__()
    candidate_selector = recipe.candidate_selector_spec
    proposed_selector = recipe.proposed_selector_spec
    _validate_selector_spec(candidate_selector, "C12 candidate selector")
    _validate_selector_spec(proposed_selector, "C12 proposed selector")
    if recipe.based_on_candidate_selector_sha != candidate_selector.selector_sha:
        raise ValueError("C12 recipe does not bind its current Parent selector")
    if (
        candidate_selector.scenario_id != recipe.scenario_id
        or proposed_selector.scenario_id != recipe.scenario_id
        or proposed_selector.public_source_basis_manifest_id
        != candidate_selector.public_source_basis_manifest_id
        or proposed_selector.public_readout_basis_manifest_id
        != candidate_selector.public_readout_basis_manifest_id
    ):
        raise ValueError("C12 candidate/proposed selector basis binding mismatch")
    candidate_source_selector = frozen_tensor_array(candidate_selector.source_selector)
    candidate_readout_selector = frozen_tensor_array(
        candidate_selector.readout_selector
    )
    candidate_source = frozen_tensor_array(candidate_selector.source_injection)
    candidate_readout = frozen_tensor_array(candidate_selector.readout_coisometry)
    proposed_source_selector = frozen_tensor_array(proposed_selector.source_selector)
    proposed_readout_selector = frozen_tensor_array(proposed_selector.readout_selector)
    proposed_source = frozen_tensor_array(proposed_selector.source_injection)
    proposed_readout = frozen_tensor_array(proposed_selector.readout_coisometry)
    identity = np.eye(4, dtype=np.complex128)
    if not all(
        np.array_equal(value, identity)
        for value in (
            candidate_source_selector,
            candidate_readout_selector,
            candidate_source,
            candidate_readout,
        )
    ):
        raise ValueError("C12 current Parent selector is not exact identity4")
    if (
        proposed_source_selector.shape != (4, 2)
        or proposed_readout_selector.shape != (4, 4)
        or proposed_source.shape != (4, 2)
        or proposed_readout.shape != (4, 4)
        or proposed_selector.source_selector_derivation_id
        != "analytic-common-geometry-semantic-frame-first-two-columns-v1"
        or proposed_selector.readout_selector_derivation_id
        != "c12-inherit-current-parent-identity4-readout-v1"
        or proposed_selector.selector_sha == candidate_selector.selector_sha
    ):
        raise ValueError("C12 proposed selector/refreeze body is not frozen")
    if (
        max(
            float(
                np.linalg.norm(
                    proposed_source_selector.conj().T @ proposed_source_selector
                    - np.eye(2, dtype=np.complex128),
                    ord=2,
                )
            ),
            float(
                np.linalg.norm(
                    proposed_readout_selector @ proposed_readout_selector.conj().T
                    - identity,
                    ord=2,
                )
            ),
        )
        > 1.0e-12
    ):
        raise ValueError("C12 proposed selector is not isometric/coisometric")
    if not np.array_equal(
        proposed_source,
        candidate_source @ proposed_source_selector,
    ):
        raise ValueError("C12 proposed source is not derived from the public basis")
    if not np.array_equal(
        proposed_readout,
        proposed_readout_selector @ candidate_readout,
    ):
        raise ValueError("C12 proposed readout is not derived from the public basis")
    if not np.array_equal(proposed_readout, candidate_readout):
        raise ValueError("C12 readout changed despite its unchanged disposition")
    for step in recipe.actual_steps:
        _validate_step(step)
    if recipe.matched_ablated_steps != tuple(
        step for step in recipe.actual_steps if not step.target_conditioned
    ):
        raise ValueError("C12 matched branch is not the exact conditioned deletion")
    if recipe.semantic_frame_derivation_id != (
        "analytic-common-geometry-semantic-frame-v1"
    ):
        raise ValueError("C12 semantic frame is not the shared closed-form frame")
    expected_source = _closed_common_semantic_frame()[:, :2]
    if not np.array_equal(
        proposed_source,
        expected_source,
    ):
        raise ValueError("C12 source is not the first two closed semantic columns")
    projector_frame = _common_semantic_basis(recipe.matched_ablated_steps)[:, :2]
    expected_subspace_residual = float(
        np.linalg.norm(
            projector_frame @ projector_frame.conj().T
            - expected_source @ expected_source.conj().T,
            ord=2,
        )
    )
    if (
        recipe.projector_frame_subspace_residual != expected_subspace_residual
        or recipe.projector_frame_subspace_residual > 1.0e-12
    ):
        raise ValueError(
            "C12 projector-derived frame leaves the closed semantic subspace"
        )
    if recipe.actual_effect_digest != _executed_effect_digest(
        recipe.actual_steps,
        "actual",
    ):
        raise ValueError("C12 actual effect digest does not replay")
    if recipe.matched_ablated_effect_digest != _executed_effect_digest(
        recipe.actual_steps,
        "matched_ablated",
    ):
        raise ValueError("C12 matched effect digest does not replay")
    if recipe.recipe_sha != canonical_sha(c12_application_recipe_payload(recipe)):
        raise ValueError("C12 recipe SHA does not match its complete body")


def c12_application_recipe_symbol(
    recipe: C12ApplicationRecipe,
    momentum: float,
    branch: Literal["actual", "matched_ablated"],
) -> np.ndarray:
    """Evaluate only the local shear composite; incidence is intentionally absent."""

    _validate_recipe(recipe)
    if type(momentum) is not float or not math.isfinite(momentum):
        raise TypeError("momentum must be an exact finite fp64 value")
    if branch == "actual":
        steps = recipe.actual_steps
    elif branch == "matched_ablated":
        steps = recipe.matched_ablated_steps
    else:
        raise ValueError("C12 branch is not registered")
    return _symbol_from_steps(steps, momentum)


def _build_incidence_point(reciprocal_index: tuple[int, ...]) -> C12IncidencePointWire:
    mode = reciprocal_index[0]
    exact_nu = sp.simplify(4 * sp.sin(sp.pi * mode / 8) ** 2)
    variable = sp.Symbol("nu")
    minimal_polynomial = sp.Poly(sp.minpoly(exact_nu, variable), variable)
    polynomial_coefficients = tuple(
        int(value) for value in minimal_polynomial.all_coeffs()
    )
    nu_value = 2.0 - math.sqrt(2.0) if mode == 1 else 2.0
    momentum = 2.0 * math.pi * mode / C12_RESPONSE_TORUS_DENOMINATOR
    stencil_symbol = sum(
        coefficient * np.exp(1.0j * momentum * offset)
        for offset, coefficient in ((-1, -1), (0, 2), (1, -1))
    )
    incidence = nu_value * np.eye(4, dtype=np.complex128)
    normalized = incidence / nu_value
    provisional = C12IncidencePointWire(
        point_schema_version=C12_INCIDENCE_POINT_SCHEMA_VERSION,
        incidence_family_id=C12_INCIDENCE_FAMILY_ID,
        normalizer_formula_id=C12_NORMALIZER_FORMULA_ID,
        torus_denominator=C12_RESPONSE_TORUS_DENOMINATOR,
        reciprocal_index=reciprocal_index,
        momentum=float(momentum),
        root_of_unity_order=C12_RESPONSE_TORUS_DENOMINATOR,
        root_of_unity_power=mode,
        exact_nu_expression=str(exact_nu),
        nu_minimal_polynomial_coefficients=polynomial_coefficients,
        nu_value=float(nu_value),
        stencil_symbol_residual=float(abs(stencil_symbol - nu_value)),
        incidence_operator=freeze_complex_tensor(incidence),
        normalized_incidence_operator=freeze_complex_tensor(normalized),
        application_stage="POST_RESPONSE_READOUT_ONLY",
        point_sha="0" * 64,
    )
    return replace(
        provisional,
        point_sha=canonical_sha(c12_incidence_point_wire_payload(provisional)),
    )


def _make_c12_analytic_incidence_certificate(
) -> C12AnalyticIncidenceCertificate:
    momentum = sp.Symbol("k", real=True)
    normalizer = 4 * sp.sin(momentum / 2) ** 2
    centered_symbol = 2 - sp.exp(sp.I * momentum) - sp.exp(-sp.I * momentum)
    if sp.simplify(centered_symbol - normalizer) != 0:
        raise AssertionError("centered stencil did not reproduce nu_inc")
    ir_limit = sp.simplify(sp.limit(normalizer / momentum**2, momentum, 0))
    if ir_limit != 1:
        raise AssertionError("centered incidence did not produce the exact IR limit")
    provisional = C12AnalyticIncidenceCertificate(
        certificate_schema_version=(
            C12_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION
        ),
        incidence_family_id=C12_INCIDENCE_FAMILY_ID,
        normalizer_formula_id=C12_NORMALIZER_FORMULA_ID,
        normalizer_derivation_id=C12_NORMALIZER_DERIVATION_ID,
        stencil_offsets=((-1,), (0,), (1,)),
        stencil_coefficients=(-1, 2, -1),
        first_brillouin_domain_id=(
            "one-dimensional-minus-pi-open-pi-closed-v1"
        ),
        ir_limit_formula_id=C12_IR_LIMIT_FORMULA_ID,
        ir_limit_order=2,
        ir_limit_value=1.0,
        ir_conclusion=C12_IR_CONCLUSION,
        positivity_certified=True,
        absolute_signal_threshold_authority_ref=(
            C12_ABSOLUTE_SIGNAL_THRESHOLD_AUTHORITY_REF
        ),
        raw_bridge_noise_evidence_ref=C12_RAW_BRIDGE_NOISE_EVIDENCE_REF,
        raw_noise_absolute_threshold_authority_ref=(
            C12_RAW_NOISE_ABSOLUTE_THRESHOLD_AUTHORITY_REF
        ),
        relative_gap_threshold_authority_ref=(
            C12_RELATIVE_GAP_THRESHOLD_AUTHORITY_REF
        ),
        point_wires=tuple(
            _build_incidence_point(index)
            for index in C12_RESPONSE_RECIPROCAL_INDICES
        ),
        certificate_sha="0" * 64,
    )
    return replace(
        provisional,
        certificate_sha=canonical_sha(
            c12_analytic_incidence_certificate_payload(provisional)
        ),
    )


def _build_ir_certificate() -> C12IRLimitCertificate:
    analytic = build_c12_analytic_incidence_certificate()
    provisional = C12IRLimitCertificate(
        certificate_schema_version=C12_IR_CERTIFICATE_SCHEMA_VERSION,
        incidence_family_id=analytic.incidence_family_id,
        normalizer_formula_id=analytic.normalizer_formula_id,
        symbol_formula_id=analytic.normalizer_derivation_id,
        stencil_offsets=analytic.stencil_offsets,
        stencil_coefficients=analytic.stencil_coefficients,
        first_brillouin_domain_id=analytic.first_brillouin_domain_id,
        ir_limit_formula_id=analytic.ir_limit_formula_id,
        ir_limit_order=analytic.ir_limit_order,
        ir_limit_value=analytic.ir_limit_value,
        positivity_certified=analytic.positivity_certified,
        point_wires=analytic.point_wires,
        certificate_sha="0" * 64,
    )
    result = replace(
        provisional,
        certificate_sha=canonical_sha(c12_ir_limit_certificate_payload(provisional)),
    )
    _validate_ir_certificate(result)
    return result


def _validate_incidence_point(point: C12IncidencePointWire) -> None:
    _exact_record(point, C12IncidencePointWire, "C12 incidence point")
    point.__post_init__()
    if point.reciprocal_index not in C12_RESPONSE_RECIPROCAL_INDICES:
        raise ValueError("C12 incidence point is not preregistered")
    expected = _build_incidence_point_body(point.reciprocal_index)
    if c12_incidence_point_wire_payload(point) != expected:
        raise ValueError("C12 incidence point differs from exact cyclotomic replay")
    for tensor in (point.incidence_operator, point.normalized_incidence_operator):
        _exact_record(tensor, FrozenComplexTensor, "C12 incidence tensor")
        verify_frozen_tensor(tensor)
    if point.point_sha != canonical_sha(c12_incidence_point_wire_payload(point)):
        raise ValueError("C12 incidence point SHA does not match its body")


def _build_incidence_point_body(
    reciprocal_index: tuple[int, ...],
) -> dict[str, object]:
    # Build a deterministic comparison body without recursively validating it.
    mode = reciprocal_index[0]
    exact_nu = sp.simplify(4 * sp.sin(sp.pi * mode / 8) ** 2)
    variable = sp.Symbol("nu")
    coefficients = tuple(
        int(value)
        for value in sp.Poly(sp.minpoly(exact_nu, variable), variable).all_coeffs()
    )
    nu_value = 2.0 - math.sqrt(2.0) if mode == 1 else 2.0
    momentum = 2.0 * math.pi * mode / 8
    stencil_symbol = sum(
        coefficient * np.exp(1.0j * momentum * offset)
        for offset, coefficient in ((-1, -1), (0, 2), (1, -1))
    )
    incidence = freeze_complex_tensor(nu_value * np.eye(4, dtype=np.complex128))
    normalized = freeze_complex_tensor(np.eye(4, dtype=np.complex128))
    return {
        "point_schema_version": C12_INCIDENCE_POINT_SCHEMA_VERSION,
        "incidence_family_id": C12_INCIDENCE_FAMILY_ID,
        "normalizer_formula_id": C12_NORMALIZER_FORMULA_ID,
        "torus_denominator": 8,
        "reciprocal_index": list(reciprocal_index),
        "momentum": float(momentum),
        "root_of_unity_order": 8,
        "root_of_unity_power": mode,
        "exact_nu_expression": str(exact_nu),
        "nu_minimal_polynomial_coefficients": list(coefficients),
        "nu_value": float(nu_value),
        "stencil_symbol_residual": float(abs(stencil_symbol - nu_value)),
        "incidence_operator_sha": incidence.tensor_sha,
        "normalized_incidence_operator_sha": normalized.tensor_sha,
        "application_stage": "POST_RESPONSE_READOUT_ONLY",
    }


def _verify_c12_analytic_incidence_certificate_body(
    certificate: C12AnalyticIncidenceCertificate,
) -> C12AnalyticIncidenceCertificate:
    _exact_record(
        certificate,
        C12AnalyticIncidenceCertificate,
        "C12 analytic incidence certificate",
    )
    certificate.__post_init__()
    observed_payload = c12_analytic_incidence_certificate_payload(certificate)
    if certificate.certificate_sha != canonical_sha(observed_payload):
        raise ValueError(
            "C12 analytic incidence certificate SHA does not match its body"
        )
    for point in certificate.point_wires:
        _validate_incidence_point(point)
    expected = _make_c12_analytic_incidence_certificate()
    expected_payload = c12_analytic_incidence_certificate_payload(expected)
    if (
        observed_payload != expected_payload
        or certificate.certificate_sha != expected.certificate_sha
    ):
        raise ValueError(
            "C12 analytic incidence certificate differs from exact replay"
        )
    return certificate


def _validate_ir_certificate(certificate: C12IRLimitCertificate) -> None:
    _exact_record(certificate, C12IRLimitCertificate, "C12 IR certificate")
    certificate.__post_init__()
    analytic = verify_c12_analytic_incidence_certificate(
        build_c12_analytic_incidence_certificate()
    )
    if (
        certificate.incidence_family_id != analytic.incidence_family_id
        or certificate.normalizer_formula_id != analytic.normalizer_formula_id
        or certificate.symbol_formula_id != analytic.normalizer_derivation_id
        or certificate.stencil_offsets != analytic.stencil_offsets
        or certificate.stencil_coefficients != analytic.stencil_coefficients
        or certificate.first_brillouin_domain_id
        != analytic.first_brillouin_domain_id
        or certificate.ir_limit_formula_id != analytic.ir_limit_formula_id
        or certificate.ir_limit_order != analytic.ir_limit_order
        or certificate.ir_limit_value != analytic.ir_limit_value
        or certificate.positivity_certified
        is not analytic.positivity_certified
        or certificate.point_wires != analytic.point_wires
    ):
        raise ValueError("C12 IR certificate does not match the centered stencil")
    for point in certificate.point_wires:
        _validate_incidence_point(point)
    if certificate.certificate_sha != canonical_sha(
        c12_ir_limit_certificate_payload(certificate)
    ):
        raise ValueError("C12 IR certificate SHA does not match its body")


def _raw_build_c12_analytic_incidence_certificate(
) -> C12AnalyticIncidenceCertificate:
    """Build the repository-closed analytic C12 incidence certificate."""

    certificate = _make_c12_analytic_incidence_certificate()
    return _verify_c12_analytic_incidence_certificate_body(certificate)


def _raw_verify_c12_analytic_incidence_certificate(
    certificate: C12AnalyticIncidenceCertificate,
) -> C12AnalyticIncidenceCertificate:
    """Verify an analytic C12 certificate against repository-owned replay."""

    return _verify_c12_analytic_incidence_certificate_body(certificate)


build_c12_analytic_incidence_certificate = freeze_rulespace_call_graph(
    _raw_build_c12_analytic_incidence_certificate
)
verify_c12_analytic_incidence_certificate = freeze_rulespace_call_graph(
    _raw_verify_c12_analytic_incidence_certificate
)
del (
    _raw_build_c12_analytic_incidence_certificate,
    _raw_verify_c12_analytic_incidence_certificate,
)


def _branch_steps(
    recipe: C12ApplicationRecipe,
    branch: str,
) -> tuple[ApplicationLocalShearStep, ...]:
    if branch == "actual":
        return recipe.actual_steps
    if branch == "matched_ablated":
        return recipe.matched_ablated_steps
    raise ValueError("C12 branch is not registered")


def _realspace_plane_wave_symbol(
    steps: tuple[ApplicationLocalShearStep, ...],
    lattice_size: int,
    mode: int,
) -> np.ndarray:
    momentum = 2.0 * math.pi * mode / lattice_size
    sites = np.arange(lattice_size, dtype=np.float64)
    phase = np.exp(1.0j * momentum * sites)
    observed = np.empty((4, 4), dtype=np.complex128)
    for source_channel in range(4):
        state = np.zeros((4, lattice_size), dtype=np.complex128)
        state[source_channel, :] = phase
        for step in steps:
            source = _CHANNEL_INDEX[step.source_channel]
            destination = _CHANNEL_INDEX[step.destination_channel]
            updated = state.copy()
            updated[destination, :] += step.coefficient * np.roll(
                state[source, :],
                -step.offset[0],
            )
            state = updated
        observed[:, source_channel] = state[:, 0]
    return observed


def _build_structure_audits(
    recipe: C12ApplicationRecipe,
) -> tuple[C12StructureAudit, ...]:
    results: list[C12StructureAudit] = []
    for branch in C12_BRANCHES:
        steps = _branch_steps(recipe, branch)
        primitive_offsets = tuple(
            (value,) for value in sorted({0, *(step.offset[0] for step in steps)})
        )
        composite_radius = sum(abs(step.offset[0]) for step in steps)
        for lattice_size, modes in ((8, (1, 2)), (16, (2, 4))):
            bridge_errors: list[float] = []
            unitary_errors: list[float] = []
            symplectic_errors: list[float] = []
            reality_errors: list[float] = []
            for mode in modes:
                momentum = float(2.0 * math.pi * mode / lattice_size)
                matrix = _symbol_from_steps(steps, momentum)
                negative = _symbol_from_steps(steps, -momentum)
                realspace = _realspace_plane_wave_symbol(
                    steps,
                    lattice_size,
                    mode,
                )
                bridge_errors.append(float(np.linalg.norm(realspace - matrix, ord=2)))
                unitary_errors.append(
                    float(
                        np.linalg.norm(
                            matrix.conj().T @ matrix - np.eye(4, dtype=np.complex128),
                            ord=2,
                        )
                    )
                )
                symplectic_errors.append(
                    float(np.linalg.norm(negative.T @ _J @ matrix - _J, ord=2))
                )
                reality_errors.append(
                    float(np.linalg.norm(negative - matrix.conj(), ord=2))
                )
            provisional = C12StructureAudit(
                audit_schema_version=C12_STRUCTURE_AUDIT_SCHEMA_VERSION,
                recipe_sha=recipe.recipe_sha,
                branch=branch,  # type: ignore[arg-type]
                lattice_size=lattice_size,
                primitive_support_offsets=primitive_offsets,
                composite_support_radius=composite_radius,
                max_bridge_error=float(max(bridge_errors)),
                max_unitary_error=float(max(unitary_errors)),
                max_symplectic_error=float(max(symplectic_errors)),
                max_reality_error=float(max(reality_errors)),
                audit_sha="0" * 64,
            )
            results.append(
                replace(
                    provisional,
                    audit_sha=canonical_sha(c12_structure_audit_payload(provisional)),
                )
            )
    return tuple(results)


def _endpoint_candidate(
    recipe: C12ApplicationRecipe,
    branch: str,
    point: C12IncidencePointWire,
    order: int,
):
    matrix = _symbol_from_steps(_branch_steps(recipe, branch), point.momentum)
    candidates = _extract_projector_candidates(
        matrix,
        np.eye(4, dtype=np.complex128),
        recipe.reference_phase_bands,
        order,
        frozen_tensor_array(recipe.proposed_selector_spec.source_injection),
        frozen_tensor_array(recipe.proposed_selector_spec.readout_coisometry),
    )
    if len(candidates) != 1:
        raise ValueError("C12 endpoint extraction is not unique")
    candidate = candidates[0]
    if candidate.rank != 2:
        raise ValueError("C12 endpoint shell is not rank two")
    return candidate


def _finite_response_at_point(
    recipe: C12ApplicationRecipe,
    branch: str,
    point: C12IncidencePointWire,
    order: int,
    *,
    matrix: Optional[np.ndarray] = None,
) -> tuple[np.ndarray, float, float]:
    endpoint = _endpoint_candidate(recipe, branch, point, order)
    symbol = (
        _symbol_from_steps(_branch_steps(recipe, branch), point.momentum)
        if matrix is None
        else matrix
    )
    response = compute_fejer_filtered_response(
        symbol,
        np.eye(4, dtype=np.complex128),
        float(endpoint.phase),
        order,
        frozen_tensor_array(recipe.proposed_selector_spec.source_injection),
        frozen_tensor_array(recipe.proposed_selector_spec.readout_coisometry),
    )
    return response, float(endpoint.phase), float(endpoint.participation)


def _build_point_audit(
    recipe: C12ApplicationRecipe,
    point: C12IncidencePointWire,
    order: int,
    branch: str,
) -> C12BranchPointAudit:
    response, shell_phase, participation = _finite_response_at_point(
        recipe,
        branch,
        point,
        order,
    )
    incidence = frozen_tensor_array(point.incidence_operator)
    normalized_incidence = frozen_tensor_array(point.normalized_incidence_operator)
    raw_response = incidence @ response
    normalized_response = normalized_incidence @ response
    raw_singular = tuple(
        float(value) for value in np.linalg.svd(raw_response, compute_uv=False)
    )
    normalized_singular = tuple(
        float(value) for value in np.linalg.svd(normalized_response, compute_uv=False)
    )
    raw_rank = int(
        np.count_nonzero(np.asarray(raw_singular) > C12_ABSOLUTE_SIGNAL_THRESHOLD)
    )
    normalized_rank = int(
        np.count_nonzero(
            np.asarray(normalized_singular) > C12_ABSOLUTE_SIGNAL_THRESHOLD
        )
    )
    normalized_bridge_errors: list[float] = []
    raw_bridge_errors: list[float] = []
    exact_symbol = _symbol_from_steps(_branch_steps(recipe, branch), point.momentum)
    for lattice_size, mode in (
        (8, point.reciprocal_index[0]),
        (16, 2 * point.reciprocal_index[0]),
    ):
        bridged_symbol = _realspace_plane_wave_symbol(
            _branch_steps(recipe, branch),
            lattice_size,
            mode,
        )
        step_bridge_error = float(np.linalg.norm(bridged_symbol - exact_symbol, ord=2))
        # This is the dimensional source/readout bridge error of the one-step
        # carrier.  Multiplication by the frozen incidence norm converts it to
        # the raw-curvature unit.  Re-running a length-T polynomial on two
        # bitwise-different fp64 matrices would instead measure accumulated
        # evaluator roundoff, not the pre-registered bridge noise quantity.
        normalized_bridge_errors.append(step_bridge_error)
        raw_bridge_errors.append(float(point.nu_value * step_bridge_error))
    normalized_bridge_noise = float(max(normalized_bridge_errors))
    raw_bridge_noise = float(max(raw_bridge_errors))
    raw_active_min = float(min(raw_singular))
    normalized_active_min = float(min(normalized_singular))
    numerical_floor = float(np.finfo(np.float64).eps * max(1.0, raw_singular[0]) * 64.0)
    relative_gap = float(raw_active_min / max(raw_bridge_noise, numerical_floor))
    provisional = C12BranchPointAudit(
        audit_schema_version=C12_BRANCH_POINT_AUDIT_SCHEMA_VERSION,
        recipe_sha=recipe.recipe_sha,
        point_sha=point.point_sha,
        selected_fejer_order=order,
        branch=branch,  # type: ignore[arg-type]
        reciprocal_index=point.reciprocal_index,
        momentum=point.momentum,
        shell_phase=shell_phase,
        endpoint_shell_rank=2,
        endpoint_participation=participation,
        nu_value=point.nu_value,
        raw_response=freeze_complex_tensor(raw_response),
        normalized_response=freeze_complex_tensor(normalized_response),
        raw_singular_values=raw_singular,
        normalized_singular_values=normalized_singular,
        raw_rank=raw_rank,
        normalized_rank=normalized_rank,
        raw_active_min=raw_active_min,
        normalized_active_min=normalized_active_min,
        raw_inactive_max=None,
        normalized_inactive_max=None,
        raw_bridge_noise=raw_bridge_noise,
        normalized_bridge_noise=normalized_bridge_noise,
        absolute_signal_margin=float(
            normalized_active_min - C12_ABSOLUTE_SIGNAL_THRESHOLD
        ),
        raw_bridge_noise_margin=float(BRIDGE_TOLERANCE - raw_bridge_noise),
        relative_gap=relative_gap,
        relative_gap_margin=float(relative_gap - RAW_GAP_MIN),
        audit_sha="0" * 64,
    )
    return replace(
        provisional,
        audit_sha=canonical_sha(c12_branch_point_audit_payload(provisional)),
    )


def _build_legacy_no_go(recipe: C12ApplicationRecipe) -> C12LegacyNoGoAudit:
    point = _build_incidence_point(C12_RESPONSE_RECIPROCAL_INDICES[0])
    matrix = _symbol_from_steps(recipe.actual_steps, point.momentum)
    endpoint = _endpoint_candidate(recipe, "actual", point, C12_FEJER_ORDERS[0])
    legacy = compute_fejer_filtered_response(
        matrix,
        np.eye(4, dtype=np.complex128),
        float(endpoint.phase),
        C12_FEJER_ORDERS[0],
        np.eye(4, dtype=np.complex128),
        np.eye(4, dtype=np.complex128),
    )
    singular_values = tuple(
        float(value) for value in np.linalg.svd(legacy, compute_uv=False)
    )
    observed_rank = int(
        np.count_nonzero(np.asarray(singular_values) > C12_ABSOLUTE_SIGNAL_THRESHOLD)
    )
    provisional = C12LegacyNoGoAudit(
        audit_schema_version=C12_LEGACY_NO_GO_SCHEMA_VERSION,
        recipe_sha=recipe.recipe_sha,
        legacy_source_id="identity4",
        legacy_declared_shell_rank=1,
        selected_fejer_order=C12_FEJER_ORDERS[0],
        reciprocal_index=point.reciprocal_index,
        singular_values=singular_values,
        observed_rank=observed_rank,
        off_band_active_min=float(min(singular_values[2:])),
        absolute_signal_threshold=C12_ABSOLUTE_SIGNAL_THRESHOLD,
        conclusion="REJECT_IDENTITY4_AND_RANK1",
        audit_sha="0" * 64,
    )
    return replace(
        provisional,
        audit_sha=canonical_sha(c12_legacy_no_go_audit_payload(provisional)),
    )


def _validate_structure_audit(audit: C12StructureAudit) -> None:
    _exact_record(audit, C12StructureAudit, "C12 structure audit")
    audit.__post_init__()
    if (
        audit.branch not in C12_BRANCHES
        or audit.lattice_size not in (8, 16)
        or audit.max_bridge_error > 2.0e-12
        or audit.max_unitary_error > 1.0e-12
        or audit.max_symplectic_error > 1.0e-12
        or audit.max_reality_error > 1.0e-12
    ):
        raise ValueError("C12 structure audit is not GREEN")
    if audit.audit_sha != canonical_sha(c12_structure_audit_payload(audit)):
        raise ValueError("C12 structure audit SHA does not match its body")


def _validate_point_audit(audit: C12BranchPointAudit) -> None:
    _exact_record(audit, C12BranchPointAudit, "C12 branch point audit")
    audit.__post_init__()
    if (
        audit.branch not in C12_BRANCHES
        or audit.reciprocal_index not in C12_RESPONSE_RECIPROCAL_INDICES
        or audit.endpoint_shell_rank != 2
        or audit.endpoint_participation <= 0.25
        or audit.raw_rank != 2
        or audit.normalized_rank != 2
        or audit.raw_inactive_max is not None
        or audit.normalized_inactive_max is not None
        or audit.absolute_signal_margin <= 0.0
        or audit.raw_bridge_noise_margin <= 0.0
        or audit.relative_gap_margin <= 0.0
    ):
        raise ValueError("C12 finite point audit is not GREEN")
    for tensor in (audit.raw_response, audit.normalized_response):
        _exact_record(tensor, FrozenComplexTensor, "C12 finite response tensor")
        verify_frozen_tensor(tensor)
        if frozen_tensor_array(tensor).shape != (4, 2):
            raise ValueError("C12 finite response tensor shape is not frozen")
    if audit.audit_sha != canonical_sha(c12_branch_point_audit_payload(audit)):
        raise ValueError("C12 point audit SHA does not match its body")


def _validate_legacy_no_go(audit: C12LegacyNoGoAudit) -> None:
    _exact_record(audit, C12LegacyNoGoAudit, "C12 legacy no-go audit")
    audit.__post_init__()
    if (
        audit.legacy_source_id != "identity4"
        or audit.legacy_declared_shell_rank != 1
        or audit.selected_fejer_order != C12_FEJER_ORDERS[0]
        or audit.reciprocal_index != C12_RESPONSE_RECIPROCAL_INDICES[0]
        or audit.observed_rank != 4
        or audit.off_band_active_min <= audit.absolute_signal_threshold
    ):
        raise ValueError("C12 legacy identity/rank-one no-go does not replay")
    if audit.audit_sha != canonical_sha(c12_legacy_no_go_audit_payload(audit)):
        raise ValueError("C12 legacy no-go SHA does not match its body")


def _validate_preflight(preflight: C12IncidencePreflight) -> None:
    _exact_record(preflight, C12IncidencePreflight, "C12 incidence preflight")
    preflight.__post_init__()
    _validate_recipe(preflight.recipe)
    _validate_ir_certificate(preflight.ir_certificate)
    if preflight.candidate_sha != preflight.recipe.candidate_sha:
        raise ValueError("C12 candidate binding does not close")
    if preflight.candidate_application_sha != (
        preflight.recipe.candidate_application_sha
    ):
        raise ValueError("C12 candidate application binding does not close")
    if preflight.candidate_scenario_sha != preflight.recipe.candidate_scenario_sha:
        raise ValueError("C12 candidate scenario binding does not close")
    if (
        preflight.absolute_signal_threshold != C12_ABSOLUTE_SIGNAL_THRESHOLD
        or preflight.raw_noise_absolute_threshold != BRIDGE_TOLERANCE
        or preflight.relative_gap_threshold != RAW_GAP_MIN
    ):
        raise ValueError("C12 preflight thresholds are not frozen references")
    expected_structure_keys = {
        (branch, lattice_size) for branch in C12_BRANCHES for lattice_size in (8, 16)
    }
    observed_structure_keys = {
        (audit.branch, audit.lattice_size) for audit in preflight.structure_audits
    }
    if (
        len(preflight.structure_audits) != len(expected_structure_keys)
        or observed_structure_keys != expected_structure_keys
    ):
        raise ValueError("C12 L8/L16 structure audit grid is incomplete")
    for audit in preflight.structure_audits:
        _validate_structure_audit(audit)
        if audit.recipe_sha != preflight.recipe.recipe_sha:
            raise ValueError("C12 structure audit recipe binding mismatch")
    expected_point_keys = {
        (order, branch, index)
        for order in C12_FEJER_ORDERS
        for branch in C12_BRANCHES
        for index in C12_RESPONSE_RECIPROCAL_INDICES
    }
    observed_point_keys = {
        (audit.selected_fejer_order, audit.branch, audit.reciprocal_index)
        for audit in preflight.point_audits
    }
    if (
        len(preflight.point_audits) != len(expected_point_keys)
        or observed_point_keys != expected_point_keys
    ):
        raise ValueError("C12 T/branch/k audit grid is incomplete")
    point_by_index = {
        point.reciprocal_index: point for point in preflight.ir_certificate.point_wires
    }
    for audit in preflight.point_audits:
        _validate_point_audit(audit)
        point = point_by_index[audit.reciprocal_index]
        if (
            audit.recipe_sha != preflight.recipe.recipe_sha
            or audit.point_sha != point.point_sha
            or audit.momentum != point.momentum
            or audit.nu_value != point.nu_value
        ):
            raise ValueError("C12 finite point audit binding mismatch")
    _validate_legacy_no_go(preflight.legacy_no_go_audit)
    if preflight.legacy_no_go_audit.recipe_sha != preflight.recipe.recipe_sha:
        raise ValueError("C12 legacy no-go recipe binding mismatch")
    if preflight.preflight_sha != canonical_sha(
        c12_incidence_preflight_payload(preflight)
    ):
        raise ValueError("C12 preflight SHA does not match its complete body")


def _build_c12_incidence_preflight(
    candidate: ParentFreezeCandidateManifest,
) -> C12IncidencePreflight:
    application, scenario = _find_c12_candidate(candidate)
    recipe = _build_recipe(candidate, application, scenario)
    ir_certificate = _build_ir_certificate()
    structure_audits = _build_structure_audits(recipe)
    point_audits = tuple(
        _build_point_audit(recipe, point, order, branch)
        for order in C12_FEJER_ORDERS
        for branch in C12_BRANCHES
        for point in ir_certificate.point_wires
    )
    provisional = C12IncidencePreflight(
        preflight_schema_version=C12_INCIDENCE_PREFLIGHT_SCHEMA_VERSION,
        candidate_sha=candidate.candidate_sha,
        candidate_application_sha=application.candidate_application_sha,
        candidate_scenario_sha=scenario.candidate_scenario_sha,
        scenario_id=C12_SCENARIO_ID,
        recipe=recipe,
        ir_certificate=ir_certificate,
        structure_audits=structure_audits,
        point_audits=point_audits,
        legacy_no_go_audit=_build_legacy_no_go(recipe),
        expected_curvature_mode_count=2,
        absolute_signal_threshold=C12_ABSOLUTE_SIGNAL_THRESHOLD,
        raw_noise_absolute_threshold=float(BRIDGE_TOLERANCE),
        relative_gap_threshold=float(RAW_GAP_MIN),
        integration_state=C12_PREFLIGHT_STATE,
        preflight_sha="0" * 64,
    )
    result = replace(
        provisional,
        preflight_sha=canonical_sha(c12_incidence_preflight_payload(provisional)),
    )
    _validate_preflight(result)
    return result


def build_c12_incidence_preflight(
    candidate: ParentFreezeCandidateManifest,
) -> C12IncidencePreflight:
    """Build the unique non-authoritative C12 construction diagnostic."""

    if type(candidate) is not ParentFreezeCandidateManifest:
        raise TypeError("candidate must be an exact ParentFreezeCandidateManifest")
    return _build_c12_incidence_preflight(candidate)


def verify_c12_incidence_preflight(
    candidate: ParentFreezeCandidateManifest,
    preflight: C12IncidencePreflight,
) -> C12IncidencePreflight:
    """Replay a C12 preflight against the current unique Parent candidate."""

    _validate_preflight(preflight)
    expected = _build_c12_incidence_preflight(candidate)
    if preflight != expected:
        raise ValueError("C12 incidence preflight differs from live replay")
    return preflight


__all__ = [
    "C12_ABSOLUTE_SIGNAL_THRESHOLD",
    "C12_ABSOLUTE_SIGNAL_THRESHOLD_AUTHORITY_REF",
    "C12_ANALYTIC_INCIDENCE_CERTIFICATE_SCHEMA_VERSION",
    "C12_BRANCH_POINT_AUDIT_SCHEMA_VERSION",
    "C12_CONTROL_CASE_ID",
    "C12_FEJER_ORDERS",
    "C12_INCIDENCE_FAMILY_ID",
    "C12_INCIDENCE_POINT_SCHEMA_VERSION",
    "C12_INCIDENCE_PREFLIGHT_SCHEMA_VERSION",
    "C12_IR_CERTIFICATE_SCHEMA_VERSION",
    "C12_IR_CONCLUSION",
    "C12_IR_LIMIT_FORMULA_ID",
    "C12_LEGACY_NO_GO_SCHEMA_VERSION",
    "C12_NORMALIZER_DERIVATION_ID",
    "C12_NORMALIZER_FORMULA_ID",
    "C12_PREFLIGHT_STATE",
    "C12_RECIPE_SCHEMA_VERSION",
    "C12_RESPONSE_MOMENTA",
    "C12_RESPONSE_RECIPROCAL_INDICES",
    "C12_RAW_BRIDGE_NOISE_EVIDENCE_REF",
    "C12_RAW_NOISE_ABSOLUTE_THRESHOLD_AUTHORITY_REF",
    "C12_RELATIVE_GAP_THRESHOLD_AUTHORITY_REF",
    "C12_SCENARIO_ID",
    "C12_STRUCTURE_AUDIT_SCHEMA_VERSION",
    "C12AnalyticIncidenceCertificate",
    "C12ApplicationRecipe",
    "C12BranchPointAudit",
    "C12IncidencePointWire",
    "C12IncidencePreflight",
    "C12IRLimitCertificate",
    "C12LegacyNoGoAudit",
    "C12StructureAudit",
    "build_c12_analytic_incidence_certificate",
    "build_c12_incidence_preflight",
    "c12_analytic_incidence_certificate_payload",
    "c12_application_recipe_payload",
    "c12_application_recipe_symbol",
    "c12_branch_point_audit_payload",
    "c12_incidence_point_wire_payload",
    "c12_incidence_preflight_payload",
    "c12_ir_limit_certificate_payload",
    "c12_legacy_no_go_audit_payload",
    "c12_structure_audit_payload",
    "verify_c12_analytic_incidence_certificate",
    "verify_c12_incidence_preflight",
]
