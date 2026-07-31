"""Full-state real-space transition measurement for V3-M0.

The transition is measured with canonical channel impulses through the same
``apply_factory_step`` executor used by production factories.  Observer
projectors are intentionally absent: the resulting kernel is square in the
complete state space.
"""

from __future__ import annotations

import math
import re
import threading
import weakref
from copy import deepcopy
from dataclasses import dataclass, replace
from typing import Callable, Literal

import numpy as np

from .evidence import canonical_sha
from .factory import (
    FrozenComplexTensor,
    VerifiedFactory,
    _reverify_verified_factory,
    apply_factory_step,
    factory_support_offsets,
    freeze_complex_tensor,
    frozen_tensor_array,
    frozen_tensor_payload,
)
from .prestructure import (
    VerifiedPrestructureAuthority,
    _reverify_verified_prestructure_authority,
)
from .replay_scope import (
    _cached_replay_is_valid,
    _record_successful_replay,
)


TRANSITION_SCHEMA_VERSION = "v3m0.measured-transition.v1"
TRANSITION_SUPPORT_SCHEMA_VERSION = "v3m0.transition-support.v1"
TRANSITION_MAX_COMPLEX_ENTRIES = 16_777_216
STATE_BASIS_CONVENTION_ID: Literal["channel-identity-v1"] = (
    "channel-identity-v1"
)
ORIGIN_CONVENTION_ID = "periodic-index-zero-origin-v1"
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


def _shape(value: object, field: str) -> tuple[int, ...]:
    if type(value) is not tuple or not value:
        raise ValueError(f"{field} must be a non-empty tuple")
    result: list[int] = []
    for index, item in enumerate(value):
        if type(item) is not int or item <= 0:
            raise ValueError(f"{field}[{index}] must be a positive int")
        result.append(item)
    return tuple(result)


def _channels(value: object) -> tuple[str, ...]:
    if type(value) is not tuple or not value:
        raise ValueError("channel_order must be a non-empty tuple")
    result = tuple(_text(item, "channel_order item") for item in value)
    if len(set(result)) != len(result):
        raise ValueError("channel_order contains duplicates")
    return result


def _support(
    value: object,
    *,
    ndim: int,
) -> tuple[tuple[int, ...], ...]:
    if type(value) is not tuple or not value:
        raise ValueError("support_offsets must be a non-empty tuple")
    result: list[tuple[int, ...]] = []
    for row_index, row in enumerate(value):
        if type(row) is not tuple or len(row) != ndim:
            raise ValueError(
                f"support_offsets[{row_index}] dimension mismatch"
            )
        normalized: list[int] = []
        for item in row:
            if type(item) is not int:
                raise TypeError("support offsets must contain ints")
            normalized.append(item)
        result.append(tuple(normalized))
    answer = tuple(result)
    if answer != tuple(sorted(set(answer))):
        raise ValueError("support_offsets must be unique and canonical")
    return answer


@dataclass(frozen=True)
class MeasuredTransition:
    transition_schema_version: str
    parent_freeze_sha: str
    prestructure_authority_sha: str
    factory_sha: str
    factory_role: Literal["actual", "matched_ablated"]
    state_schema_id: str
    channel_order: tuple[str, ...]
    spatial_shape: tuple[int, ...]
    dt: float
    boundary_manifest_id: Literal["periodic-v1"]
    state_basis_convention_id: Literal["channel-identity-v1"]
    kernel: FrozenComplexTensor
    support_offsets: tuple[tuple[int, ...], ...]
    support_sha: str
    macro_steps: Literal[1]
    transition_sha: str

    def __post_init__(self) -> None:
        _text(self.transition_schema_version, "transition_schema_version")
        for field in (
            "parent_freeze_sha",
            "prestructure_authority_sha",
            "factory_sha",
            "support_sha",
            "transition_sha",
        ):
            _sha(getattr(self, field), field)
        if self.factory_role not in ("actual", "matched_ablated"):
            raise ValueError("factory_role is not frozen")
        _text(self.state_schema_id, "state_schema_id")
        channels = _channels(self.channel_order)
        shape = _shape(self.spatial_shape, "spatial_shape")
        if type(self.dt) is not float or not math.isfinite(self.dt):
            raise TypeError("dt must be a finite fp64 wire float")
        if self.dt <= 0.0:
            raise ValueError("dt must be positive")
        if self.boundary_manifest_id != "periodic-v1":
            raise ValueError("boundary_manifest_id is not closed")
        if self.state_basis_convention_id != STATE_BASIS_CONVENTION_ID:
            raise ValueError("state basis convention is not closed")
        if not isinstance(self.kernel, FrozenComplexTensor):
            raise TypeError("kernel must be a FrozenComplexTensor")
        if self.kernel.shape != (len(channels), len(channels)) + shape:
            raise ValueError("kernel is not a square full-state tensor")
        _support(self.support_offsets, ndim=len(shape))
        if self.macro_steps != 1:
            raise ValueError("MeasuredTransition macro_steps must equal one")


def transition_support_payload(
    support_offsets: tuple[tuple[int, ...], ...],
    spatial_shape: tuple[int, ...],
    channel_order: tuple[str, ...],
    state_basis_convention_id: str,
) -> dict[str, object]:
    if type(support_offsets) is not tuple or not support_offsets:
        raise ValueError("support_offsets must be a non-empty tuple")
    return {
        "support_schema_version": TRANSITION_SUPPORT_SCHEMA_VERSION,
        "support_offsets": [list(item) for item in support_offsets],
        "spatial_shape": list(spatial_shape),
        "channel_order": list(channel_order),
        "state_basis_convention_id": state_basis_convention_id,
        "origin_convention_id": ORIGIN_CONVENTION_ID,
    }


def _tensor_record(tensor: FrozenComplexTensor) -> dict[str, object]:
    return {
        **frozen_tensor_payload(tensor),
        "tensor_sha": tensor.tensor_sha,
    }


def measured_transition_payload(
    transition: MeasuredTransition,
) -> dict[str, object]:
    if not isinstance(transition, MeasuredTransition):
        raise TypeError("transition must be a MeasuredTransition")
    return {
        "transition_schema_version": transition.transition_schema_version,
        "parent_freeze_sha": transition.parent_freeze_sha,
        "prestructure_authority_sha": (
            transition.prestructure_authority_sha
        ),
        "factory_sha": transition.factory_sha,
        "factory_role": transition.factory_role,
        "state_schema_id": transition.state_schema_id,
        "channel_order": list(transition.channel_order),
        "spatial_shape": list(transition.spatial_shape),
        "dt": transition.dt,
        "boundary_manifest_id": transition.boundary_manifest_id,
        "state_basis_convention_id": (
            transition.state_basis_convention_id
        ),
        "kernel": _tensor_record(transition.kernel),
        "support_offsets": [list(item) for item in transition.support_offsets],
        "support_sha": transition.support_sha,
        "macro_steps": transition.macro_steps,
    }


def _assert_no_wrap(
    spatial_shape: tuple[int, ...],
    support: tuple[tuple[int, ...], ...],
) -> None:
    for axis, length in enumerate(spatial_shape):
        radius = max(abs(item[axis]) for item in support)
        if length <= 2 * radius:
            raise ValueError(
                f"spatial axis {axis} violates no-wrap L_i > 2 r_i"
            )


def _outside_support_mask(
    spatial_shape: tuple[int, ...],
    support: tuple[tuple[int, ...], ...],
) -> np.ndarray:
    mask = np.ones(spatial_shape, dtype=np.bool_)
    for offset in support:
        index = tuple(
            coordinate % length
            for coordinate, length in zip(offset, spatial_shape)
        )
        mask[index] = False
    return mask


def _assert_positive_bit_zero(values: np.ndarray) -> None:
    contiguous = np.ascontiguousarray(values, dtype=np.complex128)
    if np.any(contiguous.view(np.uint64) != np.uint64(0)):
        raise ValueError(
            "transition outside declared support is not bit-exact +0.0"
        )


def _allocate_transition_kernel(
    state_count: int,
    spatial_shape: tuple[int, ...],
) -> np.ndarray:
    entry_count = (
        state_count
        * state_count
        * math.prod(spatial_shape)
    )
    if entry_count > TRANSITION_MAX_COMPLEX_ENTRIES:
        raise ValueError("transition complex-entry cap exceeded")
    return np.zeros(
        (state_count, state_count) + spatial_shape,
        dtype=np.complex128,
    )


def _bind_inputs(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> tuple[object, object]:
    factory_view = _reverify_verified_factory(factory)
    authority_view = _reverify_verified_prestructure_authority(authority)
    if factory is not authority_view.factory:
        raise ValueError(
            "factory is not the role-specific live authority factory"
        )
    if factory_view.factory.factory_sha != authority_view.authority.factory_sha:
        raise ValueError("factory SHA does not match prestructure authority")
    if factory_view.role != authority_view.authority.factory_role:
        raise ValueError("factory role does not match prestructure authority")
    return factory_view, authority_view


def _remeasure_transition(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> MeasuredTransition:
    factory_view, authority_view = _bind_inputs(factory, authority)
    payload = factory_view.factory
    spatial_shape = payload.state_shape[1:]
    stencil_support = factory_support_offsets(factory, 1)
    support = tuple(
        sorted(
            {
                tuple(-coordinate for coordinate in offset)
                for offset in stencil_support
            }
        )
    )
    _assert_no_wrap(spatial_shape, support)
    state_count = len(payload.channel_order)
    kernel = _allocate_transition_kernel(state_count, spatial_shape)
    origin = (0,) * len(spatial_shape)
    for source in range(state_count):
        impulse = np.zeros(payload.state_shape, dtype=np.complex128)
        impulse[(source,) + origin] = 1.0 + 0.0j
        output = apply_factory_step(factory, impulse)
        if output.dtype != np.dtype(np.complex128):
            raise TypeError("factory executor changed the frozen dtype")
        if output.shape != payload.state_shape:
            raise ValueError("factory executor changed the frozen state shape")
        kernel[:, source, ...] = output
    outside = _outside_support_mask(spatial_shape, support)
    if bool(np.any(outside)):
        _assert_positive_bit_zero(kernel[:, :, outside])
    frozen_kernel = freeze_complex_tensor(kernel)
    support_sha = canonical_sha(
        transition_support_payload(
            support,
            spatial_shape,
            payload.channel_order,
            STATE_BASIS_CONVENTION_ID,
        )
    )
    parent_manifest = _reverify_verified_prestructure_authority(
        authority
    ).parent.manifest
    provisional = MeasuredTransition(
        transition_schema_version=TRANSITION_SCHEMA_VERSION,
        parent_freeze_sha=parent_manifest.parent_freeze_sha,
        prestructure_authority_sha=(
            authority_view.authority.authority_sha
        ),
        factory_sha=payload.factory_sha,
        factory_role=factory_view.role,
        state_schema_id=payload.state_schema_id,
        channel_order=payload.channel_order,
        spatial_shape=spatial_shape,
        dt=payload.dt,
        boundary_manifest_id=payload.boundary_manifest_id,
        state_basis_convention_id=STATE_BASIS_CONVENTION_ID,
        kernel=frozen_kernel,
        support_offsets=support,
        support_sha=support_sha,
        macro_steps=1,
        transition_sha="0" * 64,
    )
    return replace(
        provisional,
        transition_sha=canonical_sha(
            measured_transition_payload(provisional)
        ),
    )


class VerifiedTransition:
    """Opaque transition whose canonical impulses were re-executed."""

    __slots__ = ("__transition", "__token", "__seal", "__weakref__")

    def __init__(
        self,
        token: object,
        transition: MeasuredTransition,
        seal: str,
    ) -> None:
        if token is not _ISSUANCE_TOKEN:
            raise TypeError("VerifiedTransition can only be issued here")
        object.__setattr__(
            self,
            "_VerifiedTransition__transition",
            transition,
        )
        object.__setattr__(
            self,
            "_VerifiedTransition__token",
            token,
        )
        object.__setattr__(
            self,
            "_VerifiedTransition__seal",
            seal,
        )

    def __setattr__(self, name: str, value: object) -> None:
        del name, value
        raise AttributeError("VerifiedTransition is immutable")

    @property
    def transition(self) -> MeasuredTransition:
        return self.__transition


@dataclass(frozen=True)
class _TransitionAuthority:
    transition: MeasuredTransition
    factory: VerifiedFactory
    prestructure: VerifiedPrestructureAuthority
    seal: str


def _transition_seal(transition: MeasuredTransition) -> str:
    if transition.transition_sha != canonical_sha(
        measured_transition_payload(transition)
    ):
        raise ValueError("transition_sha does not match complete body")
    return canonical_sha(
        {
            "verified_transition_schema_version": (
                "v3m0.verified-transition.v1"
            ),
            "transition": {
                **measured_transition_payload(transition),
                "transition_sha": transition.transition_sha,
            },
        }
    )


def _make_transition_authority(
    cached_replay_is_valid: Callable[..., bool] = _cached_replay_is_valid,
    record_successful_replay: Callable[..., None] = _record_successful_replay,
) -> tuple[
    Callable[..., VerifiedTransition],
    Callable[..., VerifiedTransition],
    Callable[[VerifiedTransition], _TransitionAuthority],
]:
    live: dict[
        int,
        tuple[
            weakref.ReferenceType[VerifiedTransition],
            _TransitionAuthority,
        ],
    ] = {}
    lock = threading.RLock()

    def register_measured(
        transition: MeasuredTransition,
        factory: VerifiedFactory,
        prestructure: VerifiedPrestructureAuthority,
    ) -> VerifiedTransition:
        seal = _transition_seal(transition)
        authority = _TransitionAuthority(
            transition=deepcopy(transition),
            factory=factory,
            prestructure=prestructure,
            seal=seal,
        )
        wrapper = VerifiedTransition(_ISSUANCE_TOKEN, transition, seal)
        identity = id(wrapper)

        def remove(
            reference: weakref.ReferenceType[VerifiedTransition],
            wrapper_id: int = identity,
        ) -> None:
            with lock:
                current = live.get(wrapper_id)
                if current is not None and current[0] is reference:
                    del live[wrapper_id]

        reference = weakref.ref(wrapper, remove)
        with lock:
            live[identity] = (reference, authority)
        return wrapper

    def issue(
        transition: MeasuredTransition,
        factory: VerifiedFactory,
        prestructure: VerifiedPrestructureAuthority,
    ) -> VerifiedTransition:
        expected = _remeasure_transition(factory, prestructure)
        if transition.transition_sha != expected.transition_sha:
            raise ValueError(
                "transition does not match real-space impulse remeasurement"
            )
        return register_measured(transition, factory, prestructure)

    def reverify(wrapper: VerifiedTransition) -> _TransitionAuthority:
        if type(wrapper) is not VerifiedTransition:
            raise TypeError(
                "runtime requires a module-issued VerifiedTransition"
            )
        with lock:
            current = live.get(id(wrapper))
            if current is None or current[0]() is not wrapper:
                raise ValueError("VerifiedTransition identity is not live")
            authority = current[1]
        try:
            token = object.__getattribute__(
                wrapper,
                "_VerifiedTransition__token",
            )
            transition = object.__getattribute__(
                wrapper,
                "_VerifiedTransition__transition",
            )
            seal = object.__getattribute__(
                wrapper,
                "_VerifiedTransition__seal",
            )
        except AttributeError as exc:
            raise ValueError(
                "VerifiedTransition authority record is incomplete"
            ) from exc
        namespace = "rulespace_v3.dynamics.VerifiedTransition"

        def cheap_validator() -> None:
            try:
                body_mismatch = transition != authority.transition
            except (AttributeError, IndexError, TypeError) as exc:
                raise ValueError(
                    "VerifiedTransition exposed body is malformed"
                ) from exc
            if body_mismatch or seal != authority.seal:
                raise ValueError(
                    "VerifiedTransition cached immutable guard mismatch"
                )

        if cached_replay_is_valid(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=VerifiedTransition,
            token=token,
            exposed_bodies=(transition,),
            seal=seal,
            authority=authority,
            authority_digest=authority.seal,
            cheap_validator=cheap_validator,
        ):
            return authority
        if token is not _ISSUANCE_TOKEN:
            raise ValueError("VerifiedTransition token mismatch")
        expected = _remeasure_transition(
            authority.factory,
            authority.prestructure,
        )
        expected_seal = _transition_seal(expected)
        if (
            transition != authority.transition
            or transition.transition_sha != expected.transition_sha
            or seal != authority.seal
            or seal != expected_seal
        ):
            raise ValueError("VerifiedTransition immutable seal mismatch")
        record_successful_replay(
            namespace=namespace,
            wrapper=wrapper,
            expected_type=VerifiedTransition,
            token=token,
            exposed_bodies=(transition,),
            seal=seal,
            authority=authority,
            authority_digest=authority.seal,
        )
        return authority

    return issue, register_measured, reverify


(
    _issue_verified_transition,
    _register_measured_transition,
    _reverify_verified_transition,
) = _make_transition_authority()


def measure_transition(
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> VerifiedTransition:
    """Measure the one-step square transition from canonical impulses."""

    transition = _remeasure_transition(factory, authority)
    return _register_measured_transition(transition, factory, authority)


def verify_measured_transition(
    transition: MeasuredTransition,
    factory: VerifiedFactory,
    authority: VerifiedPrestructureAuthority,
) -> VerifiedTransition:
    """Hydrate raw evidence only after executor remeasurement."""

    if not isinstance(transition, MeasuredTransition):
        raise TypeError("transition must be a MeasuredTransition")
    if transition.transition_schema_version != TRANSITION_SCHEMA_VERSION:
        raise ValueError("unexpected transition_schema_version")
    if transition.support_sha != canonical_sha(
        transition_support_payload(
            transition.support_offsets,
            transition.spatial_shape,
            transition.channel_order,
            transition.state_basis_convention_id,
        )
    ):
        raise ValueError("support_sha does not match declared support")
    if transition.transition_sha != canonical_sha(
        measured_transition_payload(transition)
    ):
        raise ValueError("transition_sha does not match complete body")
    expected = _remeasure_transition(factory, authority)
    if transition.transition_sha != expected.transition_sha:
        raise ValueError(
            "raw transition does not match executor remeasurement"
        )
    return _register_measured_transition(transition, factory, authority)


def transition_kernel_array(
    transition: VerifiedTransition,
) -> np.ndarray:
    """Return a fresh non-authoritative array copy of the verified kernel."""

    authority = _reverify_verified_transition(transition)
    return frozen_tensor_array(authority.transition.kernel)


def transition_symbol(
    transition: VerifiedTransition,
    momentum: np.ndarray,
) -> np.ndarray:
    """Evaluate ``sum_d K[d] exp(-i k·d)`` from verified support only."""

    authority = _reverify_verified_transition(transition)
    return _transition_symbol_from_raw(authority.transition, momentum)


def _transition_symbol_from_raw(
    raw: MeasuredTransition,
    momentum: np.ndarray,
) -> np.ndarray:
    """Package-private deterministic Fourier evaluator used after authority."""

    if type(momentum) is not np.ndarray:
        raise TypeError("momentum must be a NumPy ndarray")
    if momentum.dtype != np.dtype(np.float64):
        raise TypeError("momentum dtype must be float64")
    if momentum.shape != (len(raw.spatial_shape),):
        raise ValueError("momentum dimension does not match transition")
    if not np.isfinite(momentum).all():
        raise ValueError("momentum must be finite")
    kernel = frozen_tensor_array(raw.kernel)
    result = np.zeros(
        (len(raw.channel_order), len(raw.channel_order)),
        dtype=np.complex128,
    )
    for offset in raw.support_offsets:
        index = tuple(
            coordinate % length
            for coordinate, length in zip(offset, raw.spatial_shape)
        )
        phase_argument = -float(
            sum(
                float(momentum[axis]) * coordinate
                for axis, coordinate in enumerate(offset)
            )
        )
        phase = np.exp(np.complex128(1.0j * phase_argument))
        result += kernel[(slice(None), slice(None)) + index] * phase
    return result


__all__ = [
    "STATE_BASIS_CONVENTION_ID",
    "ORIGIN_CONVENTION_ID",
    "TRANSITION_SCHEMA_VERSION",
    "TRANSITION_SUPPORT_SCHEMA_VERSION",
    "TRANSITION_MAX_COMPLEX_ENTRIES",
    "MeasuredTransition",
    "VerifiedTransition",
    "measure_transition",
    "measured_transition_payload",
    "transition_kernel_array",
    "transition_support_payload",
    "transition_symbol",
    "verify_measured_transition",
]
