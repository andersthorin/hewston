from __future__ import annotations

from typing import Any, Protocol

from backend.domain.models import BacktestSummary, Dataset


class CatalogPort(Protocol):
    def get_backtest(self, run_id: str) -> dict[str, Any] | None: ...

    def list_backtests(
        self,
        *,
        symbol: str | None = None,
        strategy_id: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 20,
        offset: int = 0,
        order: str = "-created_at",
    ) -> tuple[list[BacktestSummary], int]:
        """Return (items, total)."""
        ...

    def get_dataset(self, dataset_id: str) -> Dataset | None: ...

    # Stubs for later
    def upsert_dataset(self, dataset: dict[str, Any]) -> None:
        raise NotImplementedError

    def create_backtest(self, *args: Any, **kwargs: Any) -> str:
        raise NotImplementedError

    def set_backtest_status(self, *args: Any, **kwargs: Any) -> None:
        raise NotImplementedError

    def find_backtest_by_input_hash(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        raise NotImplementedError

    def find_backtest_by_idempotency_key(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        raise NotImplementedError
