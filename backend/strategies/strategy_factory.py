"""Strategy registry/factory utilities for building strategies."""

from __future__ import annotations

from typing import Any


class StrategyRegistry:
    """Registry mapping strategy_id to dotted import path."""

    def __init__(self) -> None:
        """Initialize an empty registry and register built-ins."""
        self._registry: dict[str, str] = {}
        # Built-ins (MVP)
        self.register("sma_crossover", "backend.strategies.sma:SMAStrategy")

    def register(self, strategy_id: str, dotted_path: str) -> None:
        """Register a strategy path.

        Args:
            strategy_id: Identifier key.
            dotted_path: Module path "pkg.mod:Class".
        """
        self._registry[strategy_id] = dotted_path

    def get(self, strategy_id: str) -> str:
        """Return dotted import path for a strategy_id.

        Raises:
            KeyError: If id is unknown.
        """
        if strategy_id not in self._registry:
            raise KeyError(f"Unknown strategy_id: {strategy_id}")
        return self._registry[strategy_id]


class StrategyFactory:
    """Factory to construct strategy instances from a registry."""

    def __init__(self, registry: StrategyRegistry | None = None) -> None:
        """Create a factory with the given registry.

        Args:
            registry: Optional custom registry; defaults to built-in.
        """
        self._registry = registry or StrategyRegistry()

    def build(self, strategy_id: str, params: dict[str, Any]):
        """Instantiate a strategy by id with params."""
        mod_path, cls_name = self._registry.get(strategy_id).split(":", 1)
        module = __import__(mod_path, fromlist=[cls_name])
        cls = getattr(module, cls_name)
        return cls(**params)
