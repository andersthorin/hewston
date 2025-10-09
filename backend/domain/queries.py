"""Common query/DTO types for backend domain operations."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class BacktestListQuery:
    """Query parameters for listing backtests.

    Fields mirror HTTP query params but are used internally to avoid
    PLR0913 violations across layers.
    """

    symbol: str | None = None
    strategy_id: str | None = None
    from_date: str | None = None
    to_date: str | None = None
    limit: int = 20
    offset: int = 0
    order: str = "-created_at"
