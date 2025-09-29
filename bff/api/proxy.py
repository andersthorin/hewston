"""
BFF Proxy API Routes

Provides transparent proxy functionality for existing backend APIs.
Maintains exact API compatibility while adding BFF-specific enhancements.
"""

from fastapi import APIRouter, Request, Depends, Query
from fastapi.responses import Response
import httpx
import logging
from typing import Optional, Dict, Any
import json

from bff.app.dependencies import get_backend_client
from bff.services.backend_client import BackendClient, create_backend_client

router = APIRouter()
logger = logging.getLogger("bff.proxy")


async def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request state."""
    return getattr(request.state, 'correlation_id', 'unknown')


async def get_backend_proxy_client(
    backend_client: httpx.AsyncClient = Depends(get_backend_client)
) -> BackendClient:
    """Get configured backend proxy client."""
    return await create_backend_client(backend_client)


# Backtests API Proxy Routes

@router.post("/backtests")
async def proxy_create_backtest(
    request: Request,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    Proxy POST /backtests to backend.
    
    Creates a new backtest run with the same API contract as the backend.
    """
    # Get request body
    body = await request.body()
    
    # Forward request to backend
    return await backend_client.proxy_request(
        method="POST",
        path="/backtests",
        headers=dict(request.headers),
        body=body,
        correlation_id=correlation_id,
    )


@router.get("/backtests")
async def proxy_list_backtests(
    request: Request,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
    # Query parameters matching backend API
    limit: int = 20,
    offset: int = 0,
    symbol: Optional[str] = None,
    strategy_id: Optional[str] = None,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
    order: Optional[str] = None,
):
    """
    Proxy GET /backtests to backend.
    
    Lists backtest runs with the same filtering and pagination as the backend.
    """
    # Prepare query parameters
    params = {
        "limit": limit,
        "offset": offset,
    }
    
    # Add optional parameters
    if symbol:
        params["symbol"] = symbol
    if strategy_id:
        params["strategy_id"] = strategy_id
    if from_date:
        params["from"] = from_date
    if to_date:
        params["to"] = to_date
    if order:
        params["order"] = order
    
    # Forward request to backend
    return await backend_client.proxy_request(
        method="GET",
        path="/backtests",
        headers=dict(request.headers),
        params=params,
        correlation_id=correlation_id,
    )


@router.get("/backtests/{run_id}")
async def proxy_get_backtest(
    run_id: str,
    request: Request,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """
    Proxy GET /backtests/{run_id} to backend.
    
    Gets a specific backtest run details.
    """
    return await backend_client.proxy_request(
        method="GET",
        path=f"/backtests/{run_id}",
        headers=dict(request.headers),
        correlation_id=correlation_id,
    )


# Bars API Proxy Routes

@router.get("/bars/daily")
async def proxy_get_daily_bars(
    symbol: str,
    from_date: Optional[str] = Query(None, alias="from"),
    to_date: Optional[str] = Query(None, alias="to"),
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
