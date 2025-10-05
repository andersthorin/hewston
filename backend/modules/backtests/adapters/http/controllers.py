from __future__ import annotations

from typing import Any, Optional, Tuple

# Thin HTTP controllers delegating to existing services (pilot exemplar)
from backend.services.backtests import (
    list_backtests_service as _list_backtests_service,
    get_backtest_service as _get_backtest_service,
    create_backtest_service as _create_backtest_service,
)


def list_backtests(
    *,
    symbol: Optional[str] = None,
    strategy_id: Optional[str] = None,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 20,
    offset: int = 0,
    order: Optional[str] = None,
) -> dict[str, Any]:
    """List backtests via application service.
    Preserves original response shape.
    """
    return _list_backtests_service(
        symbol=symbol,
        strategy_id=strategy_id,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
        order=order,
    )


def get_backtest(run_id: str) -> Optional[dict[str, Any]]:
    """Get a single backtest by id via application service."""
    return _get_backtest_service(run_id)


def create_backtest(body: dict, idempotency_key: str | None) -> Tuple[dict, int]:
    """Create a backtest via application service.
    Returns (payload, status_code).
    """
    return _create_backtest_service(body, idempotency_key)

