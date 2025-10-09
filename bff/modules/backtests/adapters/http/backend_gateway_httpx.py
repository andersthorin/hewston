"""HTTPX adapter implementation for the backend backtests endpoints."""

from __future__ import annotations

from http import HTTPStatus
from typing import Any

import httpx

from bff.modules.backtests.application.ports.backend_gateway import (
    BackendGatewayPort,
    ListBacktestsQuery,
)


class BackendGatewayHTTPX(BackendGatewayPort):
    """HTTPX adapter (skeleton) for backend backtests endpoints.

    Note: Not wired yet; pilot exemplar only.
    """

    def __init__(self, base_url: str, client: httpx.AsyncClient | None = None) -> None:
        """Initialize the HTTPX backend gateway adapter."""
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def create_backtest(self, body: dict, idempotency_key: str | None) -> tuple[dict, int]:
        """Create a backtest via backend API; returns JSON and status code."""
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        resp = await self.client.post("/backtests", json=body, headers=headers)
        return resp.json(), resp.status_code

    async def get_backtest(self, run_id: str) -> dict[str, Any] | None:
        """Fetch a backtest by ID; returns None if not found (404)."""
        resp = await self.client.get(f"/backtests/{run_id}")
        if resp.status_code == HTTPStatus.NOT_FOUND:
            return None
        resp.raise_for_status()
        return resp.json()

    async def list_backtests(self, query: ListBacktestsQuery) -> dict[str, Any]:
        """List backtests using optional filters and pagination."""
        params = {
            "symbol": query.symbol,
            "strategy_id": query.strategy_id,
            "run_from": query.run_from,
            "run_to": query.run_to,
            "limit": str(query.limit),
            "offset": str(query.offset),
            "order": query.order,
        }
        # remove None values
        params = {k: v for k, v in params.items() if v is not None}
        resp = await self.client.get("/backtests", params=params)
        resp.raise_for_status()
        return resp.json()
