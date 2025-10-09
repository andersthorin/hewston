"""HTTP controllers delegating to backend services for backtests.

Thin wrappers that preserve response shapes and keep routing simple.
"""

from __future__ import annotations

from typing import Any

from backend.domain.queries import BacktestListQuery
from backend.services.backtests import (
    create_backtest_service as _create_backtest_service,
)
from backend.services.backtests import (
    get_backtest_service as _get_backtest_service,
)
from backend.services.backtests import (
    list_backtests_service as _list_backtests_service,
)


def list_backtests(q: BacktestListQuery) -> dict[str, Any]:
    """List backtests via application service.

    Preserves original response shape.
    """
    return _list_backtests_service(q)


def get_backtest(run_id: str) -> dict[str, Any] | None:
    """Get a single backtest by id via application service."""
    return _get_backtest_service(run_id)


def create_backtest(body: dict, idempotency_key: str | None) -> tuple[dict, int]:
    """Create a backtest via application service.

    Returns (payload, status_code).
    """
    return _create_backtest_service(body, idempotency_key)
