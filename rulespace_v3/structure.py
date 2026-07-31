"""Mechanical structure and reality evidence for V3-M0 transitions."""

from __future__ import annotations

import math
import re
import struct
from dataclasses import dataclass, replace
from typing import Literal, Optional

import numpy as np

from .dynamics import VerifiedTransition, _reverify_verified_transition
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    VerifiedFactory,
    _reverify_verified_factory,
    frozen_tensor_array,
    frozen_tensor_payload,
)
from .prestructure import (
    FOURIER_ADJOINT_CONVENTION_ID,
    REALITY_CONVENTION_ID,
    SYNTHETIC_EVIDENCE_LANE,
    VerifiedPrestructureAuthority,
    _reverify_verified_prestructure_authority,
)


STRUCTURE_SCHEMA_VERSION = "v3m0.structure-manifest.v1"
REALITY_SCHEMA_VERSION = "v3m0.reality-certificate.v1"
POSITIVE_ZERO_PATTERN_ID: Literal["all-positive-zero-f64-v1"] = (
    "all-positive-zero-f64-v1"
)
FOURIER_REALITY_ID: Literal["m-minus-k-equals-conj-m-k-v1"] = (
    "m-minus-k-equals-conj-m-k-v1"
)
_POSITIVE_ZERO_BITS = b"\x00" * 8
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")


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


def _nonnegative_int(value: object, field: str) -> int:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value < 0:
        raise ValueError(f"{field} must be non-negative")
    return value


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {
        **frozen_tensor_payload(tensor),
        "tensor_sha": tensor.tensor_sha,
    }


@dataclass(frozen=True)
class StructureManifest:
    structure_schema_version: str
    evidence_lane: Literal[
        "synthetic-classical",
        "classical-adapter",
        "quantum",
    ]
    structure_kind: Literal["unitary", "symplectic"]
    target_spec_sha: str
    state_schema_id: str
    channel_order: tuple[str, ...]
    canonical_channel_pairs: tuple[tuple[str, str], ...]
    fourier_adjoint_convention_id: Literal[
        "same-k-dagger-v1",
        "minus-k-transpose-v1",
    ]
    structure_form: FrozenComplexTensor
    reality_convention_id: Optional[
        Literal["real-kernel-positive-zero-v1"]
    ]
    prestructure_authority_sha: str
    structure_manifest_sha: str

    def __post_init__(self) -> None:
        _text(self.structure_schema_version, "structure_schema_version")
        if self.evidence_lane not in (
            "synthetic-classical",
            "classical-adapter",
            "quantum",
        ):
            raise ValueError("evidence_lane is not closed")
        if self.structure_kind not in ("unitary", "symplectic"):
            raise ValueError("structure_kind is not closed")
        _sha(self.target_spec_sha, "target_spec_sha")
        _text(self.state_schema_id, "state_schema_id")
        if type(self.channel_order) is not tuple or not self.channel_order:
            raise ValueError("channel_order must be a non-empty tuple")
        if len(set(self.channel_order)) != len(self.channel_order):
            raise ValueError("channel_order contains duplicates")
        if type(self.canonical_channel_pairs) is not tuple:
            raise TypeError("canonical_channel_pairs must be a tuple")
        for pair in self.canonical_channel_pairs:
            if type(pair) is not tuple or len(pair) != 2:
                raise TypeError("canonical channel pairs must be string pairs")
            _text(pair[0], "canonical pair channel")
            _text(pair[1], "canonical pair channel")
        if self.fourier_adjoint_convention_id not in (
            "same-k-dagger-v1",
            "minus-k-transpose-v1",
        ):
            raise ValueError("Fourier adjoint convention is not closed")
        if type(self.structure_form) is not FrozenComplexTensor:
            raise TypeError(
                "structure_form must be an exact FrozenComplexTensor"
            )
        if self.reality_convention_id not in (
            None,
            "real-kernel-positive-zero-v1",
        ):
            raise ValueError("reality convention is not closed")
        _sha(
            self.prestructure_authority_sha,
            "prestructure_authority_sha",
        )
        _sha(self.structure_manifest_sha, "structure_manifest_sha")


@dataclass(frozen=True)
class RealityCertificate:
    reality_schema_version: str
    factory_sha: str
    transition_sha: str
    structure_manifest_sha: str
    factory_coefficient_count: int
    transition_entry_count: int
    imaginary_bit_pattern_id: Literal["all-positive-zero-f64-v1"]
    implied_fourier_identity_id: Literal[
        "m-minus-k-equals-conj-m-k-v1"
    ]
    reality_certificate_sha: str

    def __post_init__(self) -> None:
        _text(self.reality_schema_version, "reality_schema_version")
        for field in (
            "factory_sha",
            "transition_sha",
            "structure_manifest_sha",
            "reality_certificate_sha",
        ):
            _sha(getattr(self, field), field)
        _nonnegative_int(
            self.factory_coefficient_count,
            "factory_coefficient_count",
        )
        _nonnegative_int(
            self.transition_entry_count,
            "transition_entry_count",
        )
        if self.imaginary_bit_pattern_id != POSITIVE_ZERO_PATTERN_ID:
            raise ValueError("imaginary bit pattern is not closed")
        if self.implied_fourier_identity_id != FOURIER_REALITY_ID:
            raise ValueError("implied Fourier identity is not closed")


def structure_manifest_payload(
    manifest: StructureManifest,
) -> dict[str, object]:
    if not isinstance(manifest, StructureManifest):
        raise TypeError("manifest must be a StructureManifest")
    return {
        "structure_schema_version": manifest.structure_schema_version,
        "evidence_lane": manifest.evidence_lane,
        "structure_kind": manifest.structure_kind,
        "target_spec_sha": manifest.target_spec_sha,
        "state_schema_id": manifest.state_schema_id,
        "channel_order": list(manifest.channel_order),
        "canonical_channel_pairs": [
            list(item) for item in manifest.canonical_channel_pairs
        ],
        "fourier_adjoint_convention_id": (
            manifest.fourier_adjoint_convention_id
        ),
        "structure_form": _tensor_record(manifest.structure_form),
        "reality_convention_id": manifest.reality_convention_id,
        "prestructure_authority_sha": (
            manifest.prestructure_authority_sha
        ),
    }


def reality_certificate_payload(
    certificate: RealityCertificate,
) -> dict[str, object]:
    if not isinstance(certificate, RealityCertificate):
        raise TypeError("certificate must be a RealityCertificate")
    return {
        "reality_schema_version": certificate.reality_schema_version,
        "factory_sha": certificate.factory_sha,
        "transition_sha": certificate.transition_sha,
        "structure_manifest_sha": certificate.structure_manifest_sha,
        "factory_coefficient_count": (
            certificate.factory_coefficient_count
        ),
        "transition_entry_count": certificate.transition_entry_count,
        "imaginary_bit_pattern_id": (
            certificate.imaginary_bit_pattern_id
        ),
        "implied_fourier_identity_id": (
            certificate.implied_fourier_identity_id
        ),
    }


def _validate_synthetic_structure(
    manifest: StructureManifest,
) -> None:
    if manifest.evidence_lane != SYNTHETIC_EVIDENCE_LANE:
        raise ValueError("synthetic authority cannot change evidence lane")
    if manifest.structure_kind != "symplectic":
        raise ValueError("synthetic classical structure must be symplectic")
    if (
        manifest.fourier_adjoint_convention_id
        != FOURIER_ADJOINT_CONVENTION_ID
    ):
        raise ValueError("synthetic Fourier adjoint convention mismatch")
    if manifest.reality_convention_id != REALITY_CONVENTION_ID:
        raise ValueError("synthetic reality convention mismatch")
    flattened = tuple(
        channel
        for pair in manifest.canonical_channel_pairs
        for channel in pair
    )
    if flattened != manifest.channel_order:
        raise ValueError(
            "canonical pairs must cover channel_order exactly once"
        )
    omega = frozen_tensor_array(manifest.structure_form)
    state_count = len(manifest.channel_order)
    if omega.shape != (state_count, state_count):
        raise ValueError("structure form is not square full-state")
    if not np.array_equal(omega.T, -omega):
        raise ValueError("synthetic structure form is not antisymmetric")
    expected = np.zeros_like(omega)
    for index in range(0, state_count, 2):
        expected[index, index + 1] = 1.0 + 0.0j
        expected[index + 1, index] = -1.0 + 0.0j
    if not np.array_equal(omega, expected):
        raise ValueError("synthetic structure form is not canonical block-J")


def _expected_structure(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> StructureManifest:
    factory_view = _reverify_verified_factory(factory)
    authority_view = _reverify_verified_prestructure_authority(authority)
    if factory is not authority_view.factory:
        raise ValueError("structure factory is not authority-bound")
    prereg = authority_view.authority.synthetic_preregistration
    if prereg is None:
        raise ValueError(
            "this structure slice requires synthetic preregistration"
        )
    if factory_view.factory.factory_sha != prereg.factory_sha:
        raise ValueError("factory does not match synthetic preregistration")
    provisional = StructureManifest(
        structure_schema_version=STRUCTURE_SCHEMA_VERSION,
        evidence_lane=prereg.evidence_lane,
        structure_kind="symplectic",
        target_spec_sha=prereg.target_spec_sha,
        state_schema_id=prereg.state_schema_id,
        channel_order=prereg.channel_order,
        canonical_channel_pairs=prereg.canonical_channel_pairs,
        fourier_adjoint_convention_id=(
            prereg.fourier_adjoint_convention_id
        ),
        structure_form=prereg.structure_form,
        reality_convention_id=prereg.reality_convention_id,
        prestructure_authority_sha=(
            authority_view.authority.authority_sha
        ),
        structure_manifest_sha="0" * 64,
    )
    _validate_synthetic_structure(provisional)
    return replace(
        provisional,
        structure_manifest_sha=canonical_sha(
            structure_manifest_payload(provisional)
        ),
    )


def build_structure_manifest(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> StructureManifest:
    """Derive the synthetic structure manifest from pre-response authority."""

    return _expected_structure(factory, authority)


def verify_structure_manifest(
    manifest: StructureManifest,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> StructureManifest:
    if type(manifest) is not StructureManifest:
        raise TypeError("manifest must be a StructureManifest")
    if manifest.structure_schema_version != STRUCTURE_SCHEMA_VERSION:
        raise ValueError("unexpected structure schema")
    if manifest.structure_manifest_sha != canonical_sha(
        structure_manifest_payload(manifest)
    ):
        raise ValueError("structure_manifest_sha does not match complete body")
    expected = _expected_structure(factory, authority)
    if manifest.structure_manifest_sha != expected.structure_manifest_sha:
        raise ValueError("structure manifest is not authority-derived")
    return manifest


def _is_positive_zero(value: float) -> bool:
    if type(value) is not float:
        return False
    return struct.pack(">d", value) == _POSITIVE_ZERO_BITS


def _expected_reality(
    factory: VerifiedFactory,
    transition: VerifiedTransition,
    structure: StructureManifest,
) -> RealityCertificate:
    factory_view = _reverify_verified_factory(factory)
    transition_view = _reverify_verified_transition(transition)
    if transition_view.factory is not factory:
        raise ValueError("transition is not bound to reality factory")
    verified_structure = verify_structure_manifest(
        structure,
        factory,
        transition_view.prestructure,
    )
    if verified_structure.evidence_lane == "quantum":
        raise ValueError("quantum lane does not issue RealityCertificate")
    if verified_structure.reality_convention_id != REALITY_CONVENTION_ID:
        raise ValueError("classical reality convention is absent")
    coefficients = tuple(
        primitive.coefficient_wire
        for primitive in factory_view.factory.primitives
    )
    if not all(_is_positive_zero(wire[1]) for wire in coefficients):
        raise ValueError(
            "factory coefficient imaginary bits are not all +0.0"
        )
    raw_transition = transition_view.transition
    imaginary = tuple(wire[1] for wire in raw_transition.kernel.values_wire)
    if not all(_is_positive_zero(value) for value in imaginary):
        raise ValueError(
            "transition kernel imaginary bits are not all +0.0"
        )
    entry_count = math.prod(raw_transition.kernel.shape)
    provisional = RealityCertificate(
        reality_schema_version=REALITY_SCHEMA_VERSION,
        factory_sha=factory_view.factory.factory_sha,
        transition_sha=raw_transition.transition_sha,
        structure_manifest_sha=(
            verified_structure.structure_manifest_sha
        ),
        factory_coefficient_count=len(coefficients),
        transition_entry_count=entry_count,
        imaginary_bit_pattern_id=POSITIVE_ZERO_PATTERN_ID,
        implied_fourier_identity_id=FOURIER_REALITY_ID,
        reality_certificate_sha="0" * 64,
    )
    return replace(
        provisional,
        reality_certificate_sha=canonical_sha(
            reality_certificate_payload(provisional)
        ),
    )


def certify_reality(
    factory: VerifiedFactory,
    transition: VerifiedTransition,
    structure: StructureManifest,
) -> RealityCertificate:
    """Certify exact +0.0 imaginary wires and the implied Fourier identity."""

    return _expected_reality(factory, transition, structure)


def verify_reality_certificate(
    certificate: RealityCertificate,
    factory: VerifiedFactory,
    transition: VerifiedTransition,
    structure: StructureManifest,
) -> RealityCertificate:
    if type(certificate) is not RealityCertificate:
        raise TypeError("certificate must be a RealityCertificate")
    if certificate.reality_schema_version != REALITY_SCHEMA_VERSION:
        raise ValueError("unexpected reality schema")
    if certificate.reality_certificate_sha != canonical_sha(
        reality_certificate_payload(certificate)
    ):
        raise ValueError(
            "reality_certificate_sha does not match complete body"
        )
    expected = _expected_reality(factory, transition, structure)
    if (
        certificate.reality_certificate_sha
        != expected.reality_certificate_sha
    ):
        raise ValueError("reality certificate does not match exact replay")
    return certificate


__all__ = [
    "FOURIER_REALITY_ID",
    "POSITIVE_ZERO_PATTERN_ID",
    "REALITY_SCHEMA_VERSION",
    "STRUCTURE_SCHEMA_VERSION",
    "RealityCertificate",
    "StructureManifest",
    "build_structure_manifest",
    "certify_reality",
    "reality_certificate_payload",
    "structure_manifest_payload",
    "verify_reality_certificate",
    "verify_structure_manifest",
]
