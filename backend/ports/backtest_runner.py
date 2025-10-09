"""Protocol for backtest runner adapters."""

from __future__ import annotations

from typing import Any, Protocol


class BacktestRunnerPort(Protocol):
    """Abstraction over a concrete engine capable of executing a backtest."""

    def run(
        self, *, dataset_id: str, strategy_id: str, params: dict[str, Any], seed: int
    ) -> dict[str, Any]:
        """Run a backtest and return a structured result.

        Returns:
            dict[str, Any]: With keys: orders, fills, equity, metrics.
        """
        ...
