"""Exact Jordan-growth counter-witnesses for the V3-M0 stability gate."""

from __future__ import annotations

import re
import struct
from dataclasses import dataclass, replace
from typing import Literal, Optional

import numpy as np

from .dynamics import (
    MeasuredTransition,
    VerifiedTransition,
    _reverify_verified_transition,
    measured_transition_payload,
    transition_support_payload,
    verify_measured_transition,
)
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    VerifiedFactory,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
)
from .prestructure import VerifiedPrestructureAuthority


INSTABILITY_WITNESS_SCHEMA_VERSION = (
    "v3m0.instability-growth-counter-witness.v1"
)
JORDAN_WITNESS_PROFILE: Literal[
    "exact-zero-offset-jordan-2x2-v1"
] = "exact-zero-offset-jordan-2x2-v1"
JORDAN_POWER_FORMULA_ID: Literal[
    "jordan-one-one-zero-one-power-v1"
] = "jordan-one-one-zero-one-power-v1"
JORDAN_MACRO_STEP: Literal[16384] = 16_384
JORDAN_INITIAL_NORM_SQUARED: Literal[1] = 1
JORDAN_FINAL_NORM_SQUARED: Literal[268435457] = 268_435_457
JORDAN_REQUIRED_GROWTH_SQUARED_STRICT_UPPER: Literal[
    100000001
] = 100_000_001
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _sha(value: object, field: str) -> str:
    if type(value) is not str or _LOWER_SHA.fullmatch(value) is None:
        raise ValueError(f"{field} must be a lowercase SHA-256")
    return value


def _integer(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    return value


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {
        **frozen_tensor_payload(tensor),
        "tensor_sha": tensor.tensor_sha,
    }


def _verify_tensor_sha(
    tensor: FrozenComplexTensor,
    field: str,
) -> FrozenComplexTensor:
    if type(tensor) is not FrozenComplexTensor:
        raise TypeError(f"{field} must be an exact FrozenComplexTensor")
    if tensor.tensor_sha != canonical_sha(frozen_tensor_payload(tensor)):
        raise ValueError(f"{field}.tensor_sha does not match complete body")
    return tensor


def _transition_record(
    transition: MeasuredTransition,
) -> dict[str, object]:
    return {
        **measured_transition_payload(transition),
        "transition_sha": transition.transition_sha,
    }


@dataclass(frozen=True)
class InstabilityGrowthCounterWitness:
    witness_schema_version: str
    witness_profile: Literal["exact-zero-offset-jordan-2x2-v1"]
    parent_freeze_sha: str
    prestructure_authority_sha: str
    transition: MeasuredTransition
    transition_matrix: FrozenComplexTensor
    support_offsets: tuple[tuple[int, ...], ...]
    macro_step: Literal[16384]
    initial_vector: FrozenComplexTensor
    exact_power_formula_id: Literal[
        "jordan-one-one-zero-one-power-v1"
    ]
    initial_norm_squared: Literal[1]
    final_norm_squared: Literal[268435457]
    required_growth_squared_strict_upper: Literal[100000001]
    witness_sha: str

    def __post_init__(self) -> None:
        if type(self.witness_schema_version) is not str:
            raise TypeError("witness_schema_version must be a string")
        if self.witness_profile != JORDAN_WITNESS_PROFILE:
            raise ValueError("witness_profile is not closed")
        _sha(self.parent_freeze_sha, "parent_freeze_sha")
        _sha(
            self.prestructure_authority_sha,
            "prestructure_authority_sha",
        )
        if type(self.transition) is not MeasuredTransition:
            raise TypeError("transition must be a MeasuredTransition")
        if type(self.transition_matrix) is not FrozenComplexTensor:
            raise TypeError("transition_matrix must be frozen")
        if type(self.support_offsets) is not tuple:
            raise TypeError("support_offsets must be a tuple")
        for offset in self.support_offsets:
            if type(offset) is not tuple or not all(
                type(item) is int for item in offset
            ):
                raise TypeError("support_offsets must contain integer tuples")
        _integer(self.macro_step, "macro_step")
        if type(self.initial_vector) is not FrozenComplexTensor:
            raise TypeError("initial_vector must be frozen")
        if self.exact_power_formula_id != JORDAN_POWER_FORMULA_ID:
            raise ValueError("exact_power_formula_id is not closed")
        _integer(self.initial_norm_squared, "initial_norm_squared")
        _integer(self.final_norm_squared, "final_norm_squared")
        _integer(
            self.required_growth_squared_strict_upper,
            "required_growth_squared_strict_upper",
        )
        _sha(self.witness_sha, "witness_sha")


def instability_growth_counter_witness_payload(
    witness: InstabilityGrowthCounterWitness,
) -> dict[str, object]:
    if type(witness) is not InstabilityGrowthCounterWitness:
        raise TypeError(
            "witness must be an InstabilityGrowthCounterWitness"
        )
    return {
        "witness_schema_version": witness.witness_schema_version,
        "witness_profile": witness.witness_profile,
        "parent_freeze_sha": witness.parent_freeze_sha,
        "prestructure_authority_sha": (
            witness.prestructure_authority_sha
        ),
        "transition": _transition_record(witness.transition),
        "transition_matrix": _tensor_record(witness.transition_matrix),
        "support_offsets": [
            list(offset) for offset in witness.support_offsets
        ],
        "macro_step": witness.macro_step,
        "initial_vector": _tensor_record(witness.initial_vector),
        "exact_power_formula_id": witness.exact_power_formula_id,
        "initial_norm_squared": witness.initial_norm_squared,
        "final_norm_squared": witness.final_norm_squared,
        "required_growth_squared_strict_upper": (
            witness.required_growth_squared_strict_upper
        ),
    }


def _float_bits(value: float) -> bytes:
    return struct.pack(">d", float(value))


def _complex_bits_equal(value: complex, expected: complex) -> bool:
    return (
        _float_bits(float(value.real)) == _float_bits(float(expected.real))
        and _float_bits(float(value.imag))
        == _float_bits(float(expected.imag))
    )


def _jordan_matrix() -> np.ndarray:
    return np.asarray(
        [[1.0 + 0.0j, 1.0 + 0.0j], [0.0 + 0.0j, 1.0 + 0.0j]],
        dtype=np.complex128,
    )


def _initial_vector() -> np.ndarray:
    return np.asarray(
        [0.0 + 0.0j, 1.0 + 0.0j],
        dtype=np.complex128,
    )


def _raw_has_exact_jordan_profile(
    transition: MeasuredTransition,
) -> bool:
    if type(transition) is not MeasuredTransition:
        raise TypeError("transition must be a MeasuredTransition")
    if transition.transition_sha != canonical_sha(
        measured_transition_payload(transition)
    ):
        raise ValueError("transition_sha does not match complete body")
    if transition.support_sha != canonical_sha(
        transition_support_payload(
            transition.support_offsets,
            transition.spatial_shape,
            transition.channel_order,
            transition.state_basis_convention_id,
        )
    ):
        raise ValueError("support_sha does not match complete body")
    _verify_tensor_sha(transition.kernel, "transition.kernel")
    ndim = len(transition.spatial_shape)
    zero = (0,) * ndim
    if (
        len(transition.channel_order) != 2
        or transition.support_offsets != (zero,)
        or transition.kernel.shape
        != (2, 2) + transition.spatial_shape
    ):
        return False
    kernel = frozen_tensor_array(transition.kernel)
    expected_matrix = _jordan_matrix()
    for row in range(2):
        for column in range(2):
            if not _complex_bits_equal(
                complex(kernel[(row, column) + zero]),
                complex(expected_matrix[row, column]),
            ):
                return False
    for index in np.ndindex(transition.spatial_shape):
        if index == zero:
            continue
        for value in kernel[(slice(None), slice(None)) + index].flat:
            if not _complex_bits_equal(complex(value), 0.0 + 0.0j):
                return False
    return True


def _build_instability_growth_counter_witness_from_raw(
    transition: MeasuredTransition,
) -> Optional[InstabilityGrowthCounterWitness]:
    """Build only for the one closed exact-Jordan profile."""

    if not _raw_has_exact_jordan_profile(transition):
        return None
    provisional = InstabilityGrowthCounterWitness(
        witness_schema_version=INSTABILITY_WITNESS_SCHEMA_VERSION,
        witness_profile=JORDAN_WITNESS_PROFILE,
        parent_freeze_sha=transition.parent_freeze_sha,
        prestructure_authority_sha=transition.prestructure_authority_sha,
        transition=transition,
        transition_matrix=freeze_complex_tensor(_jordan_matrix()),
        support_offsets=transition.support_offsets,
        macro_step=JORDAN_MACRO_STEP,
        initial_vector=freeze_complex_tensor(_initial_vector()),
        exact_power_formula_id=JORDAN_POWER_FORMULA_ID,
        initial_norm_squared=JORDAN_INITIAL_NORM_SQUARED,
        final_norm_squared=JORDAN_FINAL_NORM_SQUARED,
        required_growth_squared_strict_upper=(
            JORDAN_REQUIRED_GROWTH_SQUARED_STRICT_UPPER
        ),
        witness_sha="0" * 64,
    )
    witness = replace(
        provisional,
        witness_sha=canonical_sha(
            instability_growth_counter_witness_payload(provisional)
        ),
    )
    return verify_instability_growth_counter_witness_arithmetic(witness)


def verify_instability_growth_counter_witness_arithmetic(
    witness: InstabilityGrowthCounterWitness,
) -> InstabilityGrowthCounterWitness:
    """Verify the closed exact-integer Jordan proof without live authority."""

    if type(witness) is not InstabilityGrowthCounterWitness:
        raise TypeError(
            "witness must be an InstabilityGrowthCounterWitness"
        )
    if witness.witness_schema_version != INSTABILITY_WITNESS_SCHEMA_VERSION:
        raise ValueError("unexpected instability witness schema")
    if witness.witness_sha != canonical_sha(
        instability_growth_counter_witness_payload(witness)
    ):
        raise ValueError("witness_sha does not match complete body")
    if not _raw_has_exact_jordan_profile(witness.transition):
        raise ValueError("transition is not the exact Jordan profile")
    if witness.parent_freeze_sha != witness.transition.parent_freeze_sha:
        raise ValueError("parent freeze binding mismatch")
    if (
        witness.prestructure_authority_sha
        != witness.transition.prestructure_authority_sha
    ):
        raise ValueError("prestructure binding mismatch")
    if witness.support_offsets != witness.transition.support_offsets:
        raise ValueError("support offsets do not match transition")
    expected_matrix = _jordan_matrix()
    _verify_tensor_sha(
        witness.transition_matrix,
        "transition_matrix",
    )
    stored_matrix = frozen_tensor_array(witness.transition_matrix)
    if stored_matrix.shape != (2, 2):
        raise ValueError("transition_matrix shape must be (2,2)")
    for value, expected in zip(stored_matrix.flat, expected_matrix.flat):
        if not _complex_bits_equal(complex(value), complex(expected)):
            raise ValueError("transition_matrix is not bit-exact Jordan")
    _verify_tensor_sha(witness.initial_vector, "initial_vector")
    stored_vector = frozen_tensor_array(witness.initial_vector)
    expected_vector = _initial_vector()
    if stored_vector.shape != (2,):
        raise ValueError("initial_vector shape must be (2,)")
    for value, expected in zip(stored_vector.flat, expected_vector.flat):
        if not _complex_bits_equal(complex(value), complex(expected)):
            raise ValueError("initial_vector is not bit-exact e2")

    integer_matrix = ((1, 1), (0, 1))
    nilpotent = tuple(
        tuple(integer_matrix[row][column] - int(row == column)
              for column in range(2))
        for row in range(2)
    )
    nilpotent_squared = tuple(
        tuple(
            sum(nilpotent[row][inner] * nilpotent[inner][column]
                for inner in range(2))
            for column in range(2)
        )
        for row in range(2)
    )
    if nilpotent == ((0, 0), (0, 0)):
        raise ValueError("Jordan nilpotent part must be nonzero")
    if nilpotent_squared != ((0, 0), (0, 0)):
        raise ValueError("Jordan nilpotent part must square to zero")
    if witness.macro_step != JORDAN_MACRO_STEP:
        raise ValueError("macro_step is not frozen")
    if witness.exact_power_formula_id != JORDAN_POWER_FORMULA_ID:
        raise ValueError("power formula is not frozen")
    if witness.initial_norm_squared != JORDAN_INITIAL_NORM_SQUARED:
        raise ValueError("initial norm is not frozen")
    exact_final = witness.macro_step * witness.macro_step + 1
    if (
        exact_final != JORDAN_FINAL_NORM_SQUARED
        or witness.final_norm_squared != exact_final
    ):
        raise ValueError("final norm does not follow the integer formula")
    if (
        witness.required_growth_squared_strict_upper
        != JORDAN_REQUIRED_GROWTH_SQUARED_STRICT_UPPER
    ):
        raise ValueError("required growth threshold is not frozen")
    if (
        witness.final_norm_squared
        <= witness.required_growth_squared_strict_upper
    ):
        raise ValueError("Jordan growth is not strictly above the threshold")
    return witness


def certify_instability_growth_counter_witness(
    transition: VerifiedTransition,
) -> Optional[InstabilityGrowthCounterWitness]:
    """Mechanically attempt the unique V3-M0 Jordan counter-profile."""

    view = _reverify_verified_transition(transition)
    return _build_instability_growth_counter_witness_from_raw(
        view.transition
    )


def verify_instability_growth_counter_witness(
    witness: InstabilityGrowthCounterWitness,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> InstabilityGrowthCounterWitness:
    """Hydrate only after live executor remeasurement of the embedded raw body."""

    verified = verify_instability_growth_counter_witness_arithmetic(witness)
    live_transition = verify_measured_transition(
        verified.transition,
        factory,
        authority,
    )
    expected = certify_instability_growth_counter_witness(live_transition)
    if expected is None or expected.witness_sha != verified.witness_sha:
        raise ValueError("counter-witness does not match live remeasurement")
    return verified


__all__ = [
    "INSTABILITY_WITNESS_SCHEMA_VERSION",
    "JORDAN_FINAL_NORM_SQUARED",
    "JORDAN_MACRO_STEP",
    "JORDAN_POWER_FORMULA_ID",
    "JORDAN_REQUIRED_GROWTH_SQUARED_STRICT_UPPER",
    "JORDAN_WITNESS_PROFILE",
    "InstabilityGrowthCounterWitness",
    "certify_instability_growth_counter_witness",
    "instability_growth_counter_witness_payload",
    "verify_instability_growth_counter_witness",
    "verify_instability_growth_counter_witness_arithmetic",
]
