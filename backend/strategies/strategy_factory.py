from __future__ import annotations

from typing import Any, Dict, Type


class StrategyRegistry:
    def __init__(self) -> None:
        self._registry: Dict[str, str] = {}
        # Built-ins (MVP)
        self.register("sma_crossover", "backend.strategies.sma:SMAStrategy")

    def register(self, strategy_id: str, dotted_path: str) -> None:
        self._registry[strategy_id] = dotted_path

    def get(self, strategy_id: str) -> str:
        if strategy_id not in self._registry:
            raise KeyError(f"Unknown strategy_id: {strategy_id}")
        return self._registry[strategy_id]


class StrategyFactory:
    def __init__(self, registry: StrategyRegistry | None = None) -> None:
        self._registry = registry or StrategyRegistry()

    def build(self, strategy_id: str, params: Dict[str, Any]):
        mod_path, cls_name = self._registry.get(strategy_id).split(":", 1)
        module = __import__(mod_path, fromlist=[cls_name])
        cls = getattr(module, cls_name)
        return cls(**params)

