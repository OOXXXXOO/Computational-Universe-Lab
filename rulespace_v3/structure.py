"""Mechanical structure and reality evidence for V3-M0 transitions."""

from __future__ import annotations

import math
import re
import struct
import sys
import types
from dataclasses import dataclass, replace
from typing import Callable, Literal, Optional

import numpy as np

from .dynamics import (
    MeasuredTransition,
    VerifiedTransition,
    _reverify_verified_transition,
)
from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    VerifiedFactory,
    _reverify_verified_factory,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
)
from .prestructure import (
    FOURIER_ADJOINT_CONVENTION_ID,
    REALITY_CONVENTION_ID,
    SYNTHETIC_APPLICATION_AUTHORITY_KIND,
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


def _freeze_owner_call_graph(root: Callable) -> Callable:
    """Detach reachable project functions while retaining live authority state."""

    function_memo: dict[int, Callable] = {}
    container_memo: dict[int, tuple[object, object]] = {}
    frozen_marker = "__structure_metric_project_frozen__"

    def is_unfrozen_project_function(value: object) -> bool:
        if type(value) is not types.FunctionType:
            return False
        function = value
        if not function.__module__.startswith("rulespace_v3."):
            return False
        if function.__dict__.get(frozen_marker) is True:
            return False
        if function.__module__ == "rulespace_v3.frozen_call_graph":
            return False
        owner = sys.modules.get(function.__module__)
        if owner is not None and function.__globals__ is not vars(owner):
            return False
        return True

    def referenced_code_names(code: types.CodeType) -> tuple[str, ...]:
        names = list(code.co_names)
        for constant in code.co_consts:
            if isinstance(constant, types.CodeType):
                names.extend(referenced_code_names(constant))
        return tuple(dict.fromkeys(names))

    def make_cell(value: object) -> object:
        def read_cell() -> object:
            return value

        return read_cell.__closure__[0]

    def contains_unfrozen_project_function(
        value: object,
        seen: Optional[set[int]] = None,
    ) -> bool:
        if is_unfrozen_project_function(value):
            return True
        if type(value) not in (tuple, list, dict):
            return False
        if seen is None:
            seen = set()
        identity = id(value)
        if identity in seen:
            return False
        seen.add(identity)
        items = value.values() if type(value) is dict else value
        return any(contains_unfrozen_project_function(item, seen) for item in items)

    def cached_container(value: object) -> object | None:
        cached = container_memo.get(id(value))
        if cached is not None and cached[0] is value:
            return cached[1]
        return None

    def freeze_container(value: object, item_freezer: Callable) -> object:
        cached = cached_container(value)
        if cached is not None:
            return cached
        if type(value) is tuple:
            result = tuple(item_freezer(item) for item in value)
            cached = cached_container(value)
            if cached is not None:
                return cached
            container_memo[id(value)] = (value, result)
            return result
        if type(value) is list:
            if not contains_unfrozen_project_function(value):
                return value
            result: list[object] = []
            container_memo[id(value)] = (value, result)
            result.extend(item_freezer(item) for item in value)
            return result
        if type(value) is dict:
            if not contains_unfrozen_project_function(value):
                return value
            result: dict[object, object] = {}
            container_memo[id(value)] = (value, result)
            result.update((key, item_freezer(item)) for key, item in value.items())
            return result
        raise TypeError("structure call-graph container type is not supported")

    def freeze_value(value: object) -> object:
        if is_unfrozen_project_function(value):
            return freeze_function(value)
        if type(value) in (tuple, list, dict):
            return freeze_container(value, freeze_value)
        return value

    def freeze_closure_value(value: object) -> object:
        if is_unfrozen_project_function(value):
            return freeze_function(value)
        if type(value) in (tuple, list, dict):
            return freeze_container(value, freeze_closure_value)
        return value

    def freeze_function(function: Callable) -> Callable:
        cached = function_memo.get(id(function))
        if cached is not None:
            return cached
        source_globals = function.__globals__
        builtins_body = source_globals.get("__builtins__", {})
        private_builtins = (
            dict(builtins_body)
            if type(builtins_body) is dict
            else dict(vars(builtins_body))
        )
        private_globals: dict[str, object] = {
            "__builtins__": private_builtins,
            "__name__": source_globals.get("__name__", function.__module__),
            "__package__": source_globals.get("__package__", None),
        }
        source_closure = function.__closure__
        private_cells = (
            None
            if source_closure is None
            else tuple(make_cell(None) for _ in source_closure)
        )
        clone = types.FunctionType(
            function.__code__,
            private_globals,
            function.__name__,
            None,
            private_cells,
        )
        function_memo[id(function)] = clone
        if source_closure is not None:
            assert private_cells is not None
            for private_cell, source_cell in zip(private_cells, source_closure):
                private_cell.cell_contents = freeze_closure_value(
                    source_cell.cell_contents
                )
        for name in referenced_code_names(function.__code__):
            if name in source_globals:
                private_globals[name] = freeze_value(source_globals[name])
        clone.__defaults__ = freeze_value(function.__defaults__)
        clone.__kwdefaults__ = freeze_value(function.__kwdefaults__)
        clone.__annotations__ = dict(function.__annotations__)
        clone.__dict__.update(function.__dict__)
        clone.__dict__[frozen_marker] = True
        clone.__qualname__ = function.__qualname__
        clone.__doc__ = function.__doc__
        clone.__module__ = function.__module__
        return clone

    return freeze_function(root)


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
    reality_convention_id: Optional[Literal["real-kernel-positive-zero-v1"]]
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
            raise TypeError("structure_form must be an exact FrozenComplexTensor")
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
    implied_fourier_identity_id: Literal["m-minus-k-equals-conj-m-k-v1"]
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


# Dataclass construction invokes ``__post_init__`` by class lookup.  Freeze
# these methods before any owner-neutral constructor captures the record types,
# so later owner-module builtin/helper rebinding cannot alter validation.
StructureManifest.__post_init__ = _freeze_owner_call_graph(
    StructureManifest.__post_init__
)
RealityCertificate.__post_init__ = _freeze_owner_call_graph(
    RealityCertificate.__post_init__
)


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
        "fourier_adjoint_convention_id": (manifest.fourier_adjoint_convention_id),
        "structure_form": _tensor_record(manifest.structure_form),
        "reality_convention_id": manifest.reality_convention_id,
        "prestructure_authority_sha": (manifest.prestructure_authority_sha),
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
        "factory_coefficient_count": (certificate.factory_coefficient_count),
        "transition_entry_count": certificate.transition_entry_count,
        "imaginary_bit_pattern_id": (certificate.imaginary_bit_pattern_id),
        "implied_fourier_identity_id": (certificate.implied_fourier_identity_id),
    }


def _validate_synthetic_structure(
    manifest: StructureManifest,
    *,
    _tensor_array_builder=frozen_tensor_array,
    _tensor_freezer=freeze_complex_tensor,
    _arrays_equal=np.array_equal,
    _zeros_like=np.zeros_like,
    _evidence_lane=SYNTHETIC_EVIDENCE_LANE,
    _adjoint_convention=FOURIER_ADJOINT_CONVENTION_ID,
    _reality_convention=REALITY_CONVENTION_ID,
) -> None:
    if manifest.evidence_lane != _evidence_lane:
        raise ValueError("synthetic authority cannot change evidence lane")
    if manifest.structure_kind != "symplectic":
        raise ValueError("synthetic classical structure must be symplectic")
    if manifest.fourier_adjoint_convention_id != _adjoint_convention:
        raise ValueError("synthetic Fourier adjoint convention mismatch")
    if manifest.reality_convention_id != _reality_convention:
        raise ValueError("synthetic reality convention mismatch")
    flattened = tuple(
        channel for pair in manifest.canonical_channel_pairs for channel in pair
    )
    if flattened != manifest.channel_order:
        raise ValueError("canonical pairs must cover channel_order exactly once")
    omega = _tensor_array_builder(manifest.structure_form)
    state_count = len(manifest.channel_order)
    if omega.shape != (state_count, state_count):
        raise ValueError("structure form is not square full-state")
    if not _arrays_equal(omega.T, -omega):
        raise ValueError("synthetic structure form is not antisymmetric")
    expected = _zeros_like(omega)
    for index in range(0, state_count, 2):
        expected[index, index + 1] = 1.0 + 0.0j
        expected[index + 1, index] = -1.0 + 0.0j
    expected_frozen = _tensor_freezer(expected)
    if (
        not _arrays_equal(omega, expected)
        or manifest.structure_form.tensor_sha != expected_frozen.tensor_sha
    ):
        raise ValueError("synthetic structure form is not canonical block-J")


_OWNER_FROZEN_CANONICAL_SHA = _freeze_owner_call_graph(canonical_sha)
_OWNER_FROZEN_STRUCTURE_PAYLOAD = _freeze_owner_call_graph(structure_manifest_payload)
_OWNER_FROZEN_STRUCTURE_VALIDATOR = _freeze_owner_call_graph(
    _validate_synthetic_structure
)


def _make_bound_synthetic_structure_manifest_core(
    *,
    manifest_type,
    validate_manifest,
    sha_builder,
    payload_builder,
    replace_fn,
    structure_schema,
    evidence_lane,
    adjoint_convention,
    reality_convention,
):
    def _build_bound_synthetic_structure_manifest(
        structure_form: FrozenComplexTensor,
        *,
        target_spec_sha: str,
        state_schema_id: str,
        channel_order: tuple[str, ...],
        canonical_channel_pairs: tuple[tuple[str, str], ...],
        prestructure_authority_sha: str,
    ) -> StructureManifest:
        """Build the owner-frozen synthetic structure from authority-bound inputs."""

        provisional = manifest_type(
            structure_schema_version=structure_schema,
            evidence_lane=evidence_lane,
            structure_kind="symplectic",
            target_spec_sha=target_spec_sha,
            state_schema_id=state_schema_id,
            channel_order=channel_order,
            canonical_channel_pairs=canonical_channel_pairs,
            fourier_adjoint_convention_id=adjoint_convention,
            structure_form=structure_form,
            reality_convention_id=reality_convention,
            prestructure_authority_sha=prestructure_authority_sha,
            structure_manifest_sha="0" * 64,
        )
        validate_manifest(provisional)
        return replace_fn(
            provisional,
            structure_manifest_sha=sha_builder(payload_builder(provisional)),
        )

    return _build_bound_synthetic_structure_manifest


_build_bound_synthetic_structure_manifest = _freeze_owner_call_graph(
    _make_bound_synthetic_structure_manifest_core(
        manifest_type=StructureManifest,
        validate_manifest=_OWNER_FROZEN_STRUCTURE_VALIDATOR,
        sha_builder=_OWNER_FROZEN_CANONICAL_SHA,
        payload_builder=_OWNER_FROZEN_STRUCTURE_PAYLOAD,
        replace_fn=replace,
        structure_schema=STRUCTURE_SCHEMA_VERSION,
        evidence_lane=SYNTHETIC_EVIDENCE_LANE,
        adjoint_convention=FOURIER_ADJOINT_CONVENTION_ID,
        reality_convention=REALITY_CONVENTION_ID,
    )
)


def _bind_structure_inputs(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
    *,
    _factory_reverifier=_reverify_verified_factory,
    _authority_reverifier=_reverify_verified_prestructure_authority,
) -> tuple[object, object]:
    factory_view = _factory_reverifier(factory)
    authority_view = _authority_reverifier(authority)
    if factory is not authority_view.factory:
        raise ValueError("structure factory is not authority-bound")
    return factory_view, authority_view


def _make_expected_structure(
    input_binder,
    structure_core,
    *,
    tensor_freezer,
    np_module,
    synthetic_authority_kind=SYNTHETIC_APPLICATION_AUTHORITY_KIND,
    synthetic_evidence_lane=SYNTHETIC_EVIDENCE_LANE,
    adjoint_convention=FOURIER_ADJOINT_CONVENTION_ID,
    reality_convention=REALITY_CONVENTION_ID,
):
    def _expected_structure(
        factory: VerifiedFactory,
        authority: VerifiedPrestructureAuthority,
    ) -> StructureManifest:
        factory_view, authority_view = input_binder(factory, authority)
        prereg = authority_view.authority.synthetic_preregistration
        if prereg is not None:
            if factory_view.factory.factory_sha != prereg.factory_sha:
                raise ValueError("factory does not match synthetic preregistration")
            if prereg.evidence_lane != synthetic_evidence_lane:
                raise ValueError("synthetic preregistration changed evidence lane")
            if prereg.fourier_adjoint_convention_id != adjoint_convention:
                raise ValueError("synthetic preregistration changed adjoint convention")
            if prereg.reality_convention_id != reality_convention:
                raise ValueError("synthetic preregistration changed reality convention")
            target_spec_sha = prereg.target_spec_sha
            state_schema_id = prereg.state_schema_id
            channel_order = prereg.channel_order
            canonical_channel_pairs = prereg.canonical_channel_pairs
            structure_form = prereg.structure_form
        elif authority_view.authority.authority_kind == synthetic_authority_kind:
            application = authority_view.authority.synthetic_application_spec
            permit_sha = authority_view.authority.synthetic_application_permit_sha
            if application is None or permit_sha is None:
                raise ValueError("synthetic application authority body is incomplete")
            payload = factory_view.factory
            channels = payload.channel_order
            if len(channels) % 2 or len(set(channels)) != len(channels):
                raise ValueError("application carrier channels are not canonical pairs")
            if (
                channels != application.basis_protocol.source_basis.channel_order
                or payload.state_schema_id
                != application.basis_protocol.source_basis.state_schema_id
            ):
                raise ValueError(
                    "application carrier interface differs from closed spec"
                )
            canonical_channel_pairs = tuple(
                (channels[index], channels[index + 1])
                for index in range(0, len(channels), 2)
            )
            omega = np_module.zeros(
                (len(channels), len(channels)),
                dtype=np_module.complex128,
            )
            for index in range(0, len(channels), 2):
                omega[index, index + 1] = 1.0 + 0.0j
                omega[index + 1, index] = -1.0 + 0.0j
            target_spec_sha = payload.target_spec_sha
            state_schema_id = payload.state_schema_id
            channel_order = channels
            structure_form = tensor_freezer(omega)
        else:
            raise ValueError("this structure slice requires synthetic preregistration")
        return structure_core(
            structure_form,
            target_spec_sha=target_spec_sha,
            state_schema_id=state_schema_id,
            channel_order=channel_order,
            canonical_channel_pairs=canonical_channel_pairs,
            prestructure_authority_sha=authority_view.authority.authority_sha,
        )

    return _expected_structure


_expected_structure = _make_expected_structure(
    _bind_structure_inputs,
    _build_bound_synthetic_structure_manifest,
    tensor_freezer=freeze_complex_tensor,
    np_module=np,
)


def _make_structure_manifest_public_apis(
    *,
    expected_builder,
    manifest_type,
    structure_schema,
    sha_builder,
    payload_builder,
):
    def build_structure_manifest(
        factory: VerifiedFactory,
        authority: VerifiedPrestructureAuthority,
    ) -> StructureManifest:
        """Derive the synthetic structure manifest from pre-response authority."""

        return expected_builder(factory, authority)

    def verify_structure_manifest(
        manifest: StructureManifest,
        factory: VerifiedFactory,
        authority: VerifiedPrestructureAuthority,
    ) -> StructureManifest:
        if type(manifest) is not manifest_type:
            raise TypeError("manifest must be a StructureManifest")
        if manifest.structure_schema_version != structure_schema:
            raise ValueError("unexpected structure schema")
        if manifest.structure_manifest_sha != sha_builder(payload_builder(manifest)):
            raise ValueError("structure_manifest_sha does not match complete body")
        expected = expected_builder(factory, authority)
        if manifest != expected:
            raise ValueError("structure manifest is not authority-derived")
        return manifest

    return build_structure_manifest, verify_structure_manifest


(
    build_structure_manifest,
    verify_structure_manifest,
) = _make_structure_manifest_public_apis(
    expected_builder=_expected_structure,
    manifest_type=StructureManifest,
    structure_schema=STRUCTURE_SCHEMA_VERSION,
    sha_builder=canonical_sha,
    payload_builder=structure_manifest_payload,
)


def _is_positive_zero(
    value: float,
    *,
    _positive_zero_bits=_POSITIVE_ZERO_BITS,
) -> bool:
    if type(value) is not float:
        return False
    return struct.pack(">d", value) == _positive_zero_bits


def _make_bound_reality_certificate_core(
    *,
    factory_reverifier,
    positive_zero_predicate,
    validate_structure,
    sha_builder,
    structure_payload_builder,
    reality_payload_builder,
    reality_type,
    transition_type,
    structure_type,
    replace_fn,
    exact_type,
    type_error,
    value_error,
    length,
    tuple_builder,
    all_predicate,
    product,
    reality_schema,
    reality_convention,
    positive_zero_pattern,
    fourier_reality,
):
    def _build_reality_certificate_from_raw(
        factory: VerifiedFactory,
        transition: MeasuredTransition,
        structure: StructureManifest,
    ) -> RealityCertificate:
        """Build exact classical reality evidence after an authority owner joins inputs."""

        factory_view = factory_reverifier(factory)
        payload = factory_view.factory
        if exact_type(transition) is not transition_type:
            raise type_error("transition must be an exact MeasuredTransition")
        if exact_type(structure) is not structure_type:
            raise type_error("structure must be an exact StructureManifest")
        if structure.structure_manifest_sha != sha_builder(
            structure_payload_builder(structure)
        ):
            raise value_error("structure manifest self-hash mismatch")
        validate_structure(structure)
        if structure.evidence_lane == "quantum":
            raise value_error("quantum lane does not issue RealityCertificate")
        if structure.reality_convention_id != reality_convention:
            raise value_error("classical reality convention is absent")
        expected_spatial_shape = payload.state_shape[1:]
        expected_kernel_shape = (
            length(payload.channel_order),
            length(payload.channel_order),
            *expected_spatial_shape,
        )
        if (
            transition.factory_sha != payload.factory_sha
            or transition.factory_role != factory_view.role
            or transition.state_schema_id != payload.state_schema_id
            or transition.channel_order != payload.channel_order
            or transition.spatial_shape != expected_spatial_shape
            or transition.dt != payload.dt
            or transition.boundary_manifest_id != payload.boundary_manifest_id
            or transition.kernel.shape != expected_kernel_shape
        ):
            raise value_error("transition does not exactly join the reality factory")
        if (
            structure.target_spec_sha != payload.target_spec_sha
            or structure.state_schema_id != payload.state_schema_id
            or structure.channel_order != payload.channel_order
            or structure.prestructure_authority_sha
            != transition.prestructure_authority_sha
        ):
            raise value_error("structure does not exactly join factory and transition")
        coefficients = tuple_builder(
            primitive.coefficient_wire for primitive in payload.primitives
        )
        if not all_predicate(positive_zero_predicate(wire[1]) for wire in coefficients):
            raise value_error("factory coefficient imaginary bits are not all +0.0")
        imaginary = tuple_builder(wire[1] for wire in transition.kernel.values_wire)
        if not all_predicate(positive_zero_predicate(value) for value in imaginary):
            raise value_error("transition kernel imaginary bits are not all +0.0")
        entry_count = product(transition.kernel.shape)
        provisional = reality_type(
            reality_schema_version=reality_schema,
            factory_sha=payload.factory_sha,
            transition_sha=transition.transition_sha,
            structure_manifest_sha=structure.structure_manifest_sha,
            factory_coefficient_count=length(coefficients),
            transition_entry_count=entry_count,
            imaginary_bit_pattern_id=positive_zero_pattern,
            implied_fourier_identity_id=fourier_reality,
            reality_certificate_sha="0" * 64,
        )
        return replace_fn(
            provisional,
            reality_certificate_sha=sha_builder(reality_payload_builder(provisional)),
        )

    return _build_reality_certificate_from_raw


_OWNER_FROZEN_POSITIVE_ZERO = _freeze_owner_call_graph(_is_positive_zero)
_OWNER_FROZEN_REALITY_PAYLOAD = _freeze_owner_call_graph(reality_certificate_payload)


_build_reality_certificate_from_raw = _freeze_owner_call_graph(
    _make_bound_reality_certificate_core(
        factory_reverifier=_reverify_verified_factory,
        positive_zero_predicate=_OWNER_FROZEN_POSITIVE_ZERO,
        validate_structure=_OWNER_FROZEN_STRUCTURE_VALIDATOR,
        sha_builder=_OWNER_FROZEN_CANONICAL_SHA,
        structure_payload_builder=_OWNER_FROZEN_STRUCTURE_PAYLOAD,
        reality_payload_builder=_OWNER_FROZEN_REALITY_PAYLOAD,
        reality_type=RealityCertificate,
        transition_type=MeasuredTransition,
        structure_type=StructureManifest,
        replace_fn=replace,
        exact_type=type,
        type_error=TypeError,
        value_error=ValueError,
        length=len,
        tuple_builder=tuple,
        all_predicate=all,
        product=math.prod,
        reality_schema=REALITY_SCHEMA_VERSION,
        reality_convention=REALITY_CONVENTION_ID,
        positive_zero_pattern=POSITIVE_ZERO_PATTERN_ID,
        fourier_reality=FOURIER_REALITY_ID,
    )
)


def _bind_reality_inputs(
    factory: VerifiedFactory,
    transition: VerifiedTransition,
    structure: StructureManifest,
    *,
    _factory_reverifier=_reverify_verified_factory,
    _transition_reverifier=_reverify_verified_transition,
    _structure_verifier=verify_structure_manifest,
) -> tuple[MeasuredTransition, StructureManifest]:
    _factory_reverifier(factory)
    transition_view = _transition_reverifier(transition)
    if transition_view.factory is not factory:
        raise ValueError("transition is not bound to reality factory")
    verified_structure = _structure_verifier(
        structure,
        factory,
        transition_view.prestructure,
    )
    return transition_view.transition, verified_structure


def _make_expected_reality(input_binder, reality_core):
    def _expected_reality(
        factory: VerifiedFactory,
        transition: VerifiedTransition,
        structure: StructureManifest,
    ) -> RealityCertificate:
        raw_transition, verified_structure = input_binder(
            factory,
            transition,
            structure,
        )
        return reality_core(factory, raw_transition, verified_structure)

    return _expected_reality


_expected_reality = _make_expected_reality(
    _bind_reality_inputs,
    _build_reality_certificate_from_raw,
)


def _make_reality_public_apis(
    *,
    expected_builder,
    reality_type,
    reality_schema,
    sha_builder,
    payload_builder,
):
    def certify_reality(
        factory: VerifiedFactory,
        transition: VerifiedTransition,
        structure: StructureManifest,
    ) -> RealityCertificate:
        """Certify exact +0.0 imaginary wires and the implied Fourier identity."""

        return expected_builder(factory, transition, structure)

    def verify_reality_certificate(
        certificate: RealityCertificate,
        factory: VerifiedFactory,
        transition: VerifiedTransition,
        structure: StructureManifest,
    ) -> RealityCertificate:
        if type(certificate) is not reality_type:
            raise TypeError("certificate must be a RealityCertificate")
        if certificate.reality_schema_version != reality_schema:
            raise ValueError("unexpected reality schema")
        if certificate.reality_certificate_sha != sha_builder(
            payload_builder(certificate)
        ):
            raise ValueError("reality_certificate_sha does not match complete body")
        expected = expected_builder(factory, transition, structure)
        if certificate != expected:
            raise ValueError("reality certificate does not match exact replay")
        return certificate

    return certify_reality, verify_reality_certificate


(
    certify_reality,
    verify_reality_certificate,
) = _make_reality_public_apis(
    expected_builder=_expected_reality,
    reality_type=RealityCertificate,
    reality_schema=REALITY_SCHEMA_VERSION,
    sha_builder=canonical_sha,
    payload_builder=reality_certificate_payload,
)


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
