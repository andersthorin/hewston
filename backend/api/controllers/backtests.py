"""HTTP controllers delegating to backend services for backtests.

Thin wrappers that preserve response shapes and keep routing simple.
"""

from __future__ import annotations

from typing import Any

from backend.services.backtests import (
    create_backtest_service as _create_backtest_service,
)
from backend.services.backtests import (
    get_backtest_service as _get_backtest_service,
)

# Thin HTTP controllers delegating to existing services (pilot exemplar)
from backend.services.backtests import (
    list_backtests_service as _list_backtests_service,
)


def list_backtests(
    *,
    symbol: str | None = None,
    strategy_id: str | None = None,
    from_date: str | None = None,
    to_date: str | None = None,
    limit: int = 20,
    offset: int = 0,
    order: str | None = None,
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


def get_backtest(run_id: str) -> dict[str, Any] | None:
    """Get a single backtest by id via application service."""
    return _get_backtest_service(run_id)


def create_backtest(body: dict, idempotency_key: str | None) -> tuple[dict, int]:
    """Create a backtest via application service.

    Returns (payload, status_code).
    """
    return _create_backtest_service(body, idempotency_key)
