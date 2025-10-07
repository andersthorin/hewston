from __future__ import annotations

from typing import Any, Protocol


class BacktestRunnerPort(Protocol):
    def run(
        self, *, dataset_id: str, strategy_id: str, params: dict[str, Any], seed: int
    ) -> dict[str, Any]:
        """Run a backtest and return a structured result.
        Returns a dict with keys: orders, fills, equity, metrics.
        """
        ...
