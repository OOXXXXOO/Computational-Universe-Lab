"""Pending typed-adapter contract for the frozen R30 tensor-complex anchor."""

from __future__ import annotations

from .contracts import AdapterContract, get_adapter_contract


def get_r30_adapter_contract(
    _getter=get_adapter_contract,
) -> AdapterContract:
    """Return the inert R30 contract; perform no legacy physics."""

    return _getter("R30")


R30_ADAPTER_CONTRACT = get_r30_adapter_contract()

__all__ = ["R30_ADAPTER_CONTRACT", "get_r30_adapter_contract"]
