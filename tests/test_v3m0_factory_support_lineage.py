from __future__ import annotations

from rulespace_v3.factory import (
    PRIMITIVE_SCHEMA_VERSION,
    Primitive,
    _primitive_sequence_support,
)


def _shear(
    step: int,
    source: str,
    destination: str,
    offset: int,
) -> Primitive:
    return Primitive(
        primitive_schema_version=PRIMITIVE_SCHEMA_VERSION,
        mechanism_id=f"mechanism-{step}",
        production_id="local_canonical_shear",
        layer_slot_id=f"layer-{step}",
        operation_id="local_canonical_shear",
        interface_id="lineage-test-interface",
        source_channel=source,
        destination_channel=destination,
        offset=(offset,),
        support_offsets=tuple(sorted(((0,), (offset,)))),
        coefficient_wire=(1.0, 0.0),
        coefficient_digest=f"{step + 1:064x}",
        neutral_identity_id=None,
    )


def test_channel_lineage_composes_dependent_shears() -> None:
    primitives = (
        _shear(0, "B", "A", 1),
        _shear(1, "A", "C", 1),
    )

    assert _primitive_sequence_support(primitives, 1) == ((0,), (1,), (2,))


def test_channel_lineage_does_not_compose_independent_shears() -> None:
    primitives = (
        _shear(0, "B", "A", 1),
        _shear(1, "D", "C", 1),
    )

    assert _primitive_sequence_support(primitives, 1) == ((0,), (1,))
