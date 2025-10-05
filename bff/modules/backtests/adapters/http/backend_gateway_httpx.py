from __future__ import annotations

from typing import Any, Optional
import httpx

from bff.modules.backtests.application.ports.backend_gateway import BackendGatewayPort


class BackendGatewayHTTPX(BackendGatewayPort):
    """HTTPX adapter (skeleton) for backend backtests endpoints.
    Note: Not wired yet; pilot exemplar only.
    """

    def __init__(self, base_url: str, client: Optional[httpx.AsyncClient] = None) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = client or httpx.AsyncClient(base_url=self.base_url, timeout=10.0)

    async def create_backtest(self, body: dict, idempotency_key: Optional[str]) -> tuple[dict, int]:
        headers = {}
        if idempotency_key:
            headers["Idempotency-Key"] = idempotency_key
        resp = await self.client.post("/backtests", json=body, headers=headers)
        return resp.json(), resp.status_code

    async def get_backtest(self, run_id: str) -> Optional[dict[str, Any]]:
        resp = await self.client.get(f"/backtests/{run_id}")
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        return resp.json()

    async def list_backtests(
        self,
        *,
        symbol: Optional[str] = None,
        strategy_id: Optional[str] = None,
        run_from: Optional[str] = None,
        run_to: Optional[str] = None,
        limit: int = 20,
        offset: int = 0,
        order: Optional[str] = None,
    ) -> dict[str, Any]:
        params = {
            "symbol": symbol,
            "strategy_id": strategy_id,
            "run_from": run_from,
            "run_to": run_to,
            "limit": str(limit),
            "offset": str(offset),
            "order": order,
        }
        # remove None values
        params = {k: v for k, v in params.items() if v is not None}
        resp = await self.client.get("/backtests", params=params)
        resp.raise_for_status()
        return resp.json()

