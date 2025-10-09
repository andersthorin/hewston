# ruff: noqa: B008

"""
BFF Proxy API Routes

Provides transparent proxy functionality for existing backend APIs.
Maintains exact API compatibility while adding BFF-specific enhancements.
"""

import logging

import httpx
from fastapi import APIRouter, Depends, Query, Request

from bff.app.dependencies import get_backend_client
from bff.services.backend_client import BackendClient, create_backend_client

router = APIRouter()
logger = logging.getLogger("bff.proxy")


async def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")


async def get_backend_proxy_client(
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
) -> BackendClient:
    """Get configured backend proxy client."""
    return await create_backend_client(backend_client)


# Backtests API Proxy Routes


# Backtests routes are owned by bff.api.backtests.
# Intentionally no proxy for /backtests here to avoid shadowing enriched handlers.


# Bars API Proxy Routes


@router.get("/bars/daily")
async def proxy_get_daily_bars(
    symbol: str,
    from_date: str | None = Query(None, alias="from"),
    to_date: str | None = Query(None, alias="to"),
    request: Request = None,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    Proxy GET /bars/daily to backend.

    Gets daily OHLCV bars for a symbol.
    """
    # Prepare query parameters
    params = {"symbol": symbol}

    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date

    # Forward request to backend
    return await backend_client.proxy_request(
        method="GET",
        path="/bars/daily",
        headers=dict(request.headers),
        params=params,
        correlation_id=correlation_id,
    )


@router.get("/bars/minute")
async def proxy_get_minute_bars(
    symbol: str,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    rth_only: bool = True,
    request: Request = None,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    Proxy GET /bars/minute to backend.

    Gets minute OHLCV bars for a symbol.
    """
    # Prepare query parameters
    params = {
        "symbol": symbol,
        "from": from_date,
        "to": to_date,
        "rth_only": rth_only,
    }

    # Forward request to backend
    return await backend_client.proxy_request(
        method="GET",
        path="/bars/minute",
        headers=dict(request.headers),
        params=params,
        correlation_id=correlation_id,
    )


@router.get("/bars/minute_decimated")
async def proxy_get_minute_decimated_bars(
    symbol: str,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    target: int = 10000,
    rth_only: bool = True,
    request: Request = None,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    Proxy GET /bars/minute_decimated to backend.

    Gets decimated minute OHLCV bars for a symbol.
    """
    # Prepare query parameters
    params = {
        "symbol": symbol,
        "from": from_date,
        "to": to_date,
        "target": target,
        "rth_only": rth_only,
    }

    # Forward request to backend
    return await backend_client.proxy_request(
        method="GET",
        path="/bars/minute_decimated",
        headers=dict(request.headers),
        params=params,
        correlation_id=correlation_id,
    )


@router.get("/bars/hour")
async def proxy_get_hour_bars(
    symbol: str,
    from_date: str = Query(..., alias="from"),
    to_date: str = Query(..., alias="to"),
    rth_only: bool = True,
    request: Request = None,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    Proxy GET /bars/hour to backend.

    Gets hourly OHLCV bars for a symbol.
    """
    # Prepare query parameters
    params = {
        "symbol": symbol,
        "from": from_date,
        "to": to_date,
        "rth_only": rth_only,
    }

    # Forward request to backend
    return await backend_client.proxy_request(
        method="GET",
        path="/bars/hour",
        headers=dict(request.headers),
        params=params,
        correlation_id=correlation_id,
    )
