from __future__ import annotations

from typing import Protocol, Any, Optional


class BackendGatewayPort(Protocol):
    """Outbound port for communicating with backend backtests endpoints."""

    async def create_backtest(self, body: dict, idempotency_key: Optional[str]) -> tuple[dict, int]:
        ...

    async def get_backtest(self, run_id: str) -> Optional[dict[str, Any]]:
        ...

    async def list_backtests(
        self,
        *,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
        from_date: Optional[str] = None,
        to_date: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        order: Optional[str] = None,
    ) -> dict[str, Any]:
        ...

