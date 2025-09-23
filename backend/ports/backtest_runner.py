from __future__ import annotations

from typing import Protocol, Dict, Any


class BacktestRunnerPort(Protocol):
    def run(self, *, dataset_id: str, strategy_id: str, params: Dict[str, Any], seed: int) -> Dict[str, Any]:
        """Run a backtest and return a structured result.
        Returns a dict with keys: orders, fills, equity, metrics.
        """
        ...

