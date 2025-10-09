"""Catalog (persistence) port definitions for backtests and datasets."""

from __future__ import annotations

from typing import Any, Protocol

from backend.domain.models import BacktestSummary, Dataset
from backend.domain.queries import BacktestListQuery


class CatalogPort(Protocol):
    """Persistence abstraction for listing and retrieving backtests and datasets."""

    def get_backtest(self, run_id: str) -> dict[str, Any] | None:
        """Return the backtest row for the given id, or None if not found."""
        ...

    def list_backtests(self, q: BacktestListQuery) -> tuple[list[BacktestSummary], int]:
        """Return (items, total) for the given query."""
        ...

    def get_dataset(self, dataset_id: str) -> Dataset | None:
        """Return dataset row for dataset_id, or None if not found."""
        ...

    # Stubs for later
    def upsert_dataset(self, dataset: dict[str, Any]) -> None:
        """Insert or update dataset row represented by a plain dict."""
        raise NotImplementedError

    def create_backtest(self, *args: Any, **kwargs: Any) -> str:
        """Create a backtest row and return the run_id."""
        raise NotImplementedError

    def set_backtest_status(self, *args: Any, **kwargs: Any) -> None:
        """Update status and related artifact fields for a backtest row."""
        raise NotImplementedError

    def find_backtest_by_input_hash(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        """Return backtest row by canonical input hash, or None."""
        raise NotImplementedError

    def find_backtest_by_idempotency_key(self, *args: Any, **kwargs: Any) -> dict[str, Any] | None:
        """Return backtest row by idempotency key, or None."""
        raise NotImplementedError
