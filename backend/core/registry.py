"""Capability registry.

Holds every registered :class:`CapabilityStrategy`. The dispatcher asks
the registry to find a strategy that can handle a given intent. Step
1.4 ships the registry empty; capability strategies (mail, translation,
calendar, document) register themselves in their own steps.
"""
from __future__ import annotations

from typing import Any

from .base_strategy import CapabilityStrategy


class CapabilityRegistry:
    def __init__(self) -> None:
        self._strategies: list[CapabilityStrategy] = []

    def register(self, strategy: CapabilityStrategy) -> None:
        if any(existing.name == strategy.name for existing in self._strategies):
            raise ValueError(f"Capability '{strategy.name}' is already registered")
        self._strategies.append(strategy)

    def find(self, intent: dict[str, Any]) -> CapabilityStrategy | None:
        for strategy in self._strategies:
            if strategy.can_handle(intent):
                return strategy
        return None

    def all(self) -> list[CapabilityStrategy]:
        return list(self._strategies)

    def clear(self) -> None:
        self._strategies.clear()


default_registry = CapabilityRegistry()
