"""Pending typed-adapter contract for the frozen R23 Maxwell/Yee anchor."""

from __future__ import annotations

from .contracts import AdapterContract, get_adapter_contract


def get_r23_adapter_contract(
    _getter=get_adapter_contract,
) -> AdapterContract:
    """Return the inert R23 contract; perform no legacy physics."""

    return _getter("R23")


R23_ADAPTER_CONTRACT = get_r23_adapter_contract()

__all__ = ["R23_ADAPTER_CONTRACT", "get_r23_adapter_contract"]
