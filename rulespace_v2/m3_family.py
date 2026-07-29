"""M3′ Round 0 pilot manifest and family-admission checks.

The construction knobs in this module are deliberately separate from the
measured ``epsilon_geo`` and ``sigma`` coordinates.  This module does not run
physics and cannot pronounce an M3′ verdict.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Mapping


Q_LEVELS = (0, 1, 2, 3, 4)
KAPPA_C_LEVELS = (0.0, 0.005, 0.01, 0.02, 0.04, 0.08)
UNITARITY_TOL_FP64 = 1e-12


@dataclass(frozen=True)
class PilotCell:
    """One frozen core-pilot construction cell, before coordinate measurement."""

    q: int
    kappa_c: float
    eta: float = 0.0
    matter_epsilon_fixed: float = 1.0
    retune_mode: str = "actual-floquet-shell"

    def __post_init__(self) -> None:
        if self.q not in Q_LEVELS:
            raise ValueError(f"q must be one of {Q_LEVELS}, got {self.q!r}")
        if self.kappa_c not in KAPPA_C_LEVELS:
            raise ValueError(
                f"kappa_c must be one of {KAPPA_C_LEVELS}, got {self.kappa_c!r}"
            )
        if self.eta != 0.0:
            raise ValueError("the core M3′ pilot fixes eta=0")
        if self.matter_epsilon_fixed != 1.0:
            raise ValueError("the core M3′ pilot fixes epsilon_mat=1")
        if self.retune_mode != "actual-floquet-shell":
            raise ValueError("the M3′ pilot requires actual-Floquet-shell retuning")

    @property
    def cell_id(self) -> str:
        kappa_token = f"{self.kappa_c:.3f}".replace(".", "p")
        return f"m3-q{self.q}-kc{kappa_token}"

    def as_dict(self) -> dict[str, object]:
        """Serialize construction inputs without fabricating measured axes."""

        return {
            "cell_id": self.cell_id,
            "q": self.q,
            "kappa_c": self.kappa_c,
            "eta": self.eta,
            "matter_epsilon_fixed": self.matter_epsilon_fixed,
            "retune_mode": self.retune_mode,
        }


def build_pilot_manifest() -> tuple[PilotCell, ...]:
    """Return the preregistered 5×6 Round 1 core-pilot manifest."""

    return tuple(
        PilotCell(q=q, kappa_c=kappa_c)
        for q in Q_LEVELS
        for kappa_c in KAPPA_C_LEVELS
    )


def legacy_rc3ii_descriptor() -> dict[str, object]:
    """Describe the frozen RC3-(ii) R2 object without upgrading its semantics."""

    return {
        "name": "RC3-(ii)-R2-partial-Yee",
        "construction_kind": "spectral_bookkeeping",
        "realspace_step_factory": None,
        "support_radius": None,
        "declared_composition_radius": None,
        "support_radius_independent_of_L": False,
        "unitarity_error_fp64": None,
        "same_state_space_all_q": True,
        "k_dependent_projection": True,
        "explicit_local_shears": [],
        "q_layer_counts": list(Q_LEVELS),
        "coordinates_are_measured": True,
        "floquet_retune_mode": "not-applicable-no-realspace-step",
        "evidence": (
            "experiments/rc3ii_relaxation_framework.py:"
            "candidate_R2 projects selected S_curv modes into ker(C) per k"
        ),
    }


def _finite_nonnegative_int(value: object) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and value >= 0
        and isfinite(float(value))
    )


def _finite_number_at_most(value: object, ceiling: float) -> bool:
    return (
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and isfinite(float(value))
        and 0.0 <= float(value) <= ceiling
    )


def audit_family_descriptor(
    descriptor: Mapping[str, object],
) -> dict[str, object]:
    """Audit whether a descriptor is eligible for an executable M3′ pilot."""

    construction_kind = descriptor.get("construction_kind")
    support_radius = descriptor.get("support_radius")
    declared_radius = descriptor.get("declared_composition_radius")
    measured_fields_absent = not any(
        field in descriptor for field in ("epsilon_geo", "sigma")
    )

    checks = {
        "strict_local_realspace": construction_kind == "strict_local_realspace",
        "realspace_step_factory": isinstance(
            descriptor.get("realspace_step_factory"), str
        )
        and bool(str(descriptor["realspace_step_factory"]).strip()),
        "finite_support_radius": _finite_nonnegative_int(support_radius),
        "declared_radius_matches": _finite_nonnegative_int(support_radius)
        and support_radius == declared_radius,
        "support_radius_independent_of_L": (
            descriptor.get("support_radius_independent_of_L") is True
        ),
        "unitarity_fp64": _finite_number_at_most(
            descriptor.get("unitarity_error_fp64"), UNITARITY_TOL_FP64
        ),
        "same_state_space_all_q": descriptor.get("same_state_space_all_q") is True,
        "no_k_dependent_projection": (
            descriptor.get("k_dependent_projection") is False
        ),
        "explicit_local_shears": isinstance(
            descriptor.get("explicit_local_shears"), (list, tuple)
        )
        and len(descriptor["explicit_local_shears"]) >= len(Q_LEVELS) - 1,
        "q_layer_mapping": tuple(descriptor.get("q_layer_counts", ())) == Q_LEVELS,
        "coordinates_are_measured": (
            descriptor.get("coordinates_are_measured") is True
        ),
        "no_measured_coordinate_injection": measured_fields_absent,
        "actual_floquet_shell_retune": (
            descriptor.get("floquet_retune_mode") == "actual-floquet-shell"
        ),
    }

    failures: list[str] = []
    if not checks["strict_local_realspace"]:
        failures.append(
            "spectral_bookkeeping_only"
            if construction_kind == "spectral_bookkeeping"
            else "not_strict_local_realspace"
        )
    failure_names = (
        ("realspace_step_factory", "missing_realspace_step_factory"),
        ("finite_support_radius", "invalid_support_radius"),
        ("declared_radius_matches", "support_radius_mismatch"),
        ("support_radius_independent_of_L", "support_radius_depends_on_L"),
        ("unitarity_fp64", "unitarity_error_above_fp64_gate"),
        ("same_state_space_all_q", "state_space_changes_with_q"),
        ("no_k_dependent_projection", "k_dependent_projection"),
        ("explicit_local_shears", "missing_explicit_local_shears"),
        ("q_layer_mapping", "invalid_q_layer_mapping"),
        ("coordinates_are_measured", "coordinates_not_declared_measured"),
        ("no_measured_coordinate_injection", "measured_coordinate_injection"),
        ("actual_floquet_shell_retune", "invalid_floquet_retune"),
    )
    for check_name, failure_name in failure_names:
        if not checks[check_name]:
            failures.append(failure_name)

    return {
        "pass": not failures,
        "thresholds": {"unitarity_error_fp64_max": UNITARITY_TOL_FP64},
        "checks": checks,
        "failures": failures,
    }


__all__ = [
    "KAPPA_C_LEVELS",
    "PilotCell",
    "Q_LEVELS",
    "UNITARITY_TOL_FP64",
    "audit_family_descriptor",
    "build_pilot_manifest",
    "legacy_rc3ii_descriptor",
]
