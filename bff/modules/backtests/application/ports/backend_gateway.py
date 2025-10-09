"""Application port for backend backtests gateway.

Defines the protocol used by the BFF to communicate with the backend's backtests endpoints.
"""

from __future__ import annotations

from typing import Any, Protocol


class BackendGatewayPort(Protocol):
    """Outbound port for communicating with backend backtests endpoints."""

    async def create_backtest(
        self, body: dict, idempotency_key: str | None
    ) -> tuple[dict, int]:
        """Create a backtest and return response JSON and status code."""
        ...

    async def get_backtest(self, run_id: str) -> dict[str, Any] | None:
        """Get a backtest by ID; returns None if not found."""
        ...

    async def list_backtests(
        self,
        *,
        symbol: str | None = None,
        strategy_id: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        limit: int = 20,
        offset: int = 0,
        order: str | None = None,
    ) -> dict[str, Any]:
        """List backtests using optional filters and pagination."""
        ...
