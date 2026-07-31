"""Complete hard-arithmetic protocol binding fp64 primitives to Root64."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace
from typing import Literal

from .evidence import canonical_sha
from .fp64 import (
    DOT_OPERATION_COUNT_ID,
    DOT_ROUNDOFF_BOUND_ID,
    FROBENIUS_CONTAINMENT_ID,
    GAMMA_BOUND_METHOD_ID,
    MINIMUM_SUBNORMAL_POWER_OF_TWO,
    UNIT_ROUNDOFF_DENOMINATOR,
)
from .root64 import (
    Fp64RootOfUnityIntervalTable,
    build_root64_interval_table,
    root64_table_payload,
    verify_root64_interval_table,
)


FP64_PROTOCOL_SCHEMA_VERSION = "v3m0.fp64-enclosure-protocol.v1"
SCALAR_EXPRESSION_DAG_ID = (
    "ordered-four-real-products-and-additions-no-fma-v1"
)
GRADUAL_UNDERFLOW_ID = "real-operation-count-times-minsub-v1"
ROOT_CENTER_PROPAGATION_ID = (
    "coefficient-frobenius-sum-times-root-center-distance-v1"
)
FINITE_VALUE_POLICY = (
    "finite-normal-or-signed-zero-reject-nonzero-subnormal-ftz-nan-inf-"
    "overflow-v1"
)
OUTWARD_ROUNDING_ID = "nextafter-after-every-scalar-op-v1"
_LOWER_SHA = re.compile(r"[0-9a-f]{64}\Z")


def _exact_int(value: object, expected: int, field: str) -> None:
    if type(value) is not int:
        raise TypeError(f"{field} must be an int")
    if value != expected:
        raise ValueError(f"{field} is not frozen")


def _exact_text(value: object, expected: str, field: str) -> None:
    if type(value) is not str:
        raise TypeError(f"{field} must be a string")
    if value != expected:
        raise ValueError(f"{field} is not frozen")


@dataclass(frozen=True)
class Fp64EnclosureProtocol:
    protocol_schema_version: str
    unit_roundoff_numerator: Literal[1]
    unit_roundoff_denominator: Literal[9007199254740992]
    minimum_subnormal_numerator: Literal[1]
    minimum_subnormal_power_of_two: Literal[-1074]
    gamma_bound_method_id: Literal[
        "integer-ratio-q-u-over-one-minus-q-u-v1"
    ]
    complex_add_real_add_count: Literal[2]
    complex_multiply_real_multiply_count: Literal[4]
    complex_multiply_real_add_count: Literal[2]
    matrix_dot_operation_count_id: Literal[
        "complex-dot-real-component-q-equals-4n-minus-1-v1"
    ]
    scalar_expression_dag_id: Literal[
        "ordered-four-real-products-and-additions-no-fma-v1"
    ]
    roundoff_bound_id: Literal[
        "gamma-q-times-absolute-product-sum-plus-minsub-v1"
    ]
    gradual_underflow_additive_id: Literal[
        "real-operation-count-times-minsub-v1"
    ]
    root_center_error_propagation_id: Literal[
        "coefficient-frobenius-sum-times-root-center-distance-v1"
    ]
    frobenius_sqrt_containment_id: Literal[
        "exact-integer-ratio-square-containment-v1"
    ]
    fma_policy: Literal["forbidden"]
    reassociation_policy: Literal["forbidden"]
    finite_value_policy: Literal[
        "finite-normal-or-signed-zero-reject-nonzero-subnormal-ftz-nan-inf-overflow-v1"
    ]
    outward_rounding_id: Literal["nextafter-after-every-scalar-op-v1"]
    root_interval_table: Fp64RootOfUnityIntervalTable
    protocol_sha: str

    def __post_init__(self) -> None:
        if type(self.protocol_schema_version) is not str:
            raise TypeError("protocol_schema_version must be a string")
        _exact_int(self.unit_roundoff_numerator, 1, "unit_roundoff_numerator")
        _exact_int(
            self.unit_roundoff_denominator,
            UNIT_ROUNDOFF_DENOMINATOR,
            "unit_roundoff_denominator",
        )
        _exact_int(
            self.minimum_subnormal_numerator,
            1,
            "minimum_subnormal_numerator",
        )
        _exact_int(
            self.minimum_subnormal_power_of_two,
            MINIMUM_SUBNORMAL_POWER_OF_TWO,
            "minimum_subnormal_power_of_two",
        )
        for field, expected in (
            ("gamma_bound_method_id", GAMMA_BOUND_METHOD_ID),
            ("matrix_dot_operation_count_id", DOT_OPERATION_COUNT_ID),
            ("scalar_expression_dag_id", SCALAR_EXPRESSION_DAG_ID),
            ("roundoff_bound_id", DOT_ROUNDOFF_BOUND_ID),
            ("gradual_underflow_additive_id", GRADUAL_UNDERFLOW_ID),
            (
                "root_center_error_propagation_id",
                ROOT_CENTER_PROPAGATION_ID,
            ),
            (
                "frobenius_sqrt_containment_id",
                FROBENIUS_CONTAINMENT_ID,
            ),
            ("fma_policy", "forbidden"),
            ("reassociation_policy", "forbidden"),
            ("finite_value_policy", FINITE_VALUE_POLICY),
            ("outward_rounding_id", OUTWARD_ROUNDING_ID),
        ):
            _exact_text(getattr(self, field), expected, field)
        _exact_int(
            self.complex_add_real_add_count,
            2,
            "complex_add_real_add_count",
        )
        _exact_int(
            self.complex_multiply_real_multiply_count,
            4,
            "complex_multiply_real_multiply_count",
        )
        _exact_int(
            self.complex_multiply_real_add_count,
            2,
            "complex_multiply_real_add_count",
        )
        if not isinstance(
            self.root_interval_table,
            Fp64RootOfUnityIntervalTable,
        ):
            raise TypeError(
                "root_interval_table has the wrong record type"
            )
        if type(self.protocol_sha) is not str:
            raise TypeError("protocol_sha must be a string")
        if _LOWER_SHA.fullmatch(self.protocol_sha) is None:
            raise ValueError("protocol_sha must be a lowercase SHA-256")


def fp64_enclosure_protocol_payload(
    protocol: Fp64EnclosureProtocol,
) -> dict[str, object]:
    if not isinstance(protocol, Fp64EnclosureProtocol):
        raise TypeError("protocol must be an Fp64EnclosureProtocol")
    return {
        "protocol_schema_version": protocol.protocol_schema_version,
        "unit_roundoff_numerator": protocol.unit_roundoff_numerator,
        "unit_roundoff_denominator": protocol.unit_roundoff_denominator,
        "minimum_subnormal_numerator": (
            protocol.minimum_subnormal_numerator
        ),
        "minimum_subnormal_power_of_two": (
            protocol.minimum_subnormal_power_of_two
        ),
        "gamma_bound_method_id": protocol.gamma_bound_method_id,
        "complex_add_real_add_count": (
            protocol.complex_add_real_add_count
        ),
        "complex_multiply_real_multiply_count": (
            protocol.complex_multiply_real_multiply_count
        ),
        "complex_multiply_real_add_count": (
            protocol.complex_multiply_real_add_count
        ),
        "matrix_dot_operation_count_id": (
            protocol.matrix_dot_operation_count_id
        ),
        "scalar_expression_dag_id": protocol.scalar_expression_dag_id,
        "roundoff_bound_id": protocol.roundoff_bound_id,
        "gradual_underflow_additive_id": (
            protocol.gradual_underflow_additive_id
        ),
        "root_center_error_propagation_id": (
            protocol.root_center_error_propagation_id
        ),
        "frobenius_sqrt_containment_id": (
            protocol.frobenius_sqrt_containment_id
        ),
        "fma_policy": protocol.fma_policy,
        "reassociation_policy": protocol.reassociation_policy,
        "finite_value_policy": protocol.finite_value_policy,
        "outward_rounding_id": protocol.outward_rounding_id,
        "root_interval_table": {
            **root64_table_payload(protocol.root_interval_table),
            "table_sha": protocol.root_interval_table.table_sha,
        },
    }


def build_fp64_enclosure_protocol() -> Fp64EnclosureProtocol:
    table = build_root64_interval_table()
    provisional = Fp64EnclosureProtocol(
        protocol_schema_version=FP64_PROTOCOL_SCHEMA_VERSION,
        unit_roundoff_numerator=1,
        unit_roundoff_denominator=UNIT_ROUNDOFF_DENOMINATOR,
        minimum_subnormal_numerator=1,
        minimum_subnormal_power_of_two=MINIMUM_SUBNORMAL_POWER_OF_TWO,
        gamma_bound_method_id=GAMMA_BOUND_METHOD_ID,
        complex_add_real_add_count=2,
        complex_multiply_real_multiply_count=4,
        complex_multiply_real_add_count=2,
        matrix_dot_operation_count_id=DOT_OPERATION_COUNT_ID,
        scalar_expression_dag_id=SCALAR_EXPRESSION_DAG_ID,
        roundoff_bound_id=DOT_ROUNDOFF_BOUND_ID,
        gradual_underflow_additive_id=GRADUAL_UNDERFLOW_ID,
        root_center_error_propagation_id=ROOT_CENTER_PROPAGATION_ID,
        frobenius_sqrt_containment_id=FROBENIUS_CONTAINMENT_ID,
        fma_policy="forbidden",
        reassociation_policy="forbidden",
        finite_value_policy=FINITE_VALUE_POLICY,
        outward_rounding_id=OUTWARD_ROUNDING_ID,
        root_interval_table=table,
        protocol_sha="0" * 64,
    )
    return replace(
        provisional,
        protocol_sha=canonical_sha(
            fp64_enclosure_protocol_payload(provisional)
        ),
    )


def verify_fp64_enclosure_protocol(
    protocol: Fp64EnclosureProtocol,
) -> Fp64EnclosureProtocol:
    if type(protocol) is not Fp64EnclosureProtocol:
        raise TypeError("protocol must be an Fp64EnclosureProtocol")
    if protocol.protocol_schema_version != FP64_PROTOCOL_SCHEMA_VERSION:
        raise ValueError("unexpected fp64 protocol schema")
    verify_root64_interval_table(protocol.root_interval_table)
    if protocol.protocol_sha != canonical_sha(
        fp64_enclosure_protocol_payload(protocol)
    ):
        raise ValueError("protocol_sha does not match complete body")
    expected = build_fp64_enclosure_protocol()
    if protocol.protocol_sha != expected.protocol_sha:
        raise ValueError("protocol does not match the closed construction")
    return protocol


__all__ = [
    "FINITE_VALUE_POLICY",
    "FP64_PROTOCOL_SCHEMA_VERSION",
    "GRADUAL_UNDERFLOW_ID",
    "OUTWARD_ROUNDING_ID",
    "ROOT_CENTER_PROPAGATION_ID",
    "SCALAR_EXPRESSION_DAG_ID",
    "Fp64EnclosureProtocol",
    "build_fp64_enclosure_protocol",
    "fp64_enclosure_protocol_payload",
    "verify_fp64_enclosure_protocol",
]
