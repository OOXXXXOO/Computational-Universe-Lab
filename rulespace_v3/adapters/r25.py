"""Pending typed-adapter contract for the frozen R25 walk/constraint anchor."""

from __future__ import annotations

from .contracts import AdapterContract, get_adapter_contract


def get_r25_adapter_contract(
    _getter=get_adapter_contract,
) -> AdapterContract:
    """Return the inert R25 contract; perform no legacy physics."""

    return _getter("R25")


R25_ADAPTER_CONTRACT = get_r25_adapter_contract()

__all__ = ["R25_ADAPTER_CONTRACT", "get_r25_adapter_contract"]
