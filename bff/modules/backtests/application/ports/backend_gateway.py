from __future__ import annotations

from typing import Any, Protocol


class BackendGatewayPort(Protocol):
    """Outbound port for communicating with backend backtests endpoints."""

    async def create_backtest(
        self, body: dict, idempotency_key: str | None
    ) -> tuple[dict, int]: ...

    async def get_backtest(self, run_id: str) -> dict[str, Any] | None: ...

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
    ) -> dict[str, Any]: ...
