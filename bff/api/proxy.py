# ruff: noqa: B008

"""BFF Proxy API Routes.

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



class DailyBarsQuery:
    """Parsed query params for /bars/daily."""

    def __init__(self, request: Request) -> None:
        """Initialize from FastAPI Request query params."""
        qp = request.query_params
        self.symbol = qp.get("symbol")
        self.from_date = qp.get("from")
        self.to_date = qp.get("to")


class MinuteBarsQuery:
    """Parsed query params for /bars/minute."""

    def __init__(self, request: Request) -> None:
        """Initialize from FastAPI Request query params."""
        qp = request.query_params
        self.symbol = qp.get("symbol")
        self.from_date = qp.get("from")
        self.to_date = qp.get("to")
        r = qp.get("rth_only")
        self.rth_only = (str(r).lower() in {"true", "1", "yes"}) if r is not None else True


class MinuteDecimatedBarsQuery:
    """Parsed query params for /bars/minute_decimated."""

    def __init__(self, request: Request) -> None:
        """Initialize from FastAPI Request query params."""
        qp = request.query_params
        self.symbol = qp.get("symbol")
        self.from_date = qp.get("from")
        self.to_date = qp.get("to")
        t = qp.get("target") or qp.get("target_points")
        self.target = int(t) if t is not None else 10000
        r = qp.get("rth_only")
        self.rth_only = (str(r).lower() in {"true", "1", "yes"}) if r is not None else True


class HourBarsQuery:
    """Parsed query params for /bars/hour."""

    def __init__(self, request: Request) -> None:
        """Initialize from FastAPI Request query params."""
        qp = request.query_params
        self.symbol = qp.get("symbol")
        self.from_date = qp.get("from")
        self.to_date = qp.get("to")
        r = qp.get("rth_only")
        self.rth_only = (str(r).lower() in {"true", "1", "yes"}) if r is not None else True


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
    params: DailyBarsQuery = Depends(),
    request: Request = None,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """Proxy GET /bars/daily to backend.

    Gets daily OHLCV bars for a symbol.
    """
    # Prepare query parameters
    params_dict = {"symbol": params.symbol}

    if params.from_date:
        params_dict["from"] = params.from_date
    if params.to_date:
        params_dict["to"] = params.to_date

    # Forward request to backend
    return await backend_client.proxy_request(
        method="GET",
        path="/bars/daily",
        headers=dict(request.headers),
        params=params_dict,
        correlation_id=correlation_id,
    )


@router.get("/bars/minute")
async def proxy_get_minute_bars(
    params: MinuteBarsQuery = Depends(),
    request: Request = None,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """Proxy GET /bars/minute to backend.

    Gets minute OHLCV bars for a symbol.
    """
    # Prepare query parameters
    params_dict = {
        "symbol": params.symbol,
        "from": params.from_date,
        "to": params.to_date,
        "rth_only": params.rth_only,
    }

    # Forward request to backend
    return await backend_client.proxy_request(
        method="GET",
        path="/bars/minute",
        headers=dict(request.headers),
        params=params_dict,
        correlation_id=correlation_id,
    )


@router.get("/bars/minute_decimated")
async def proxy_get_minute_decimated_bars(
    params: MinuteDecimatedBarsQuery = Depends(),
    request: Request = None,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """Proxy GET /bars/minute_decimated to backend.

    Gets decimated minute OHLCV bars for a symbol.
    """
    # Prepare query parameters
    params_dict = {
        "symbol": params.symbol,
        "from": params.from_date,
        "to": params.to_date,
        "target": params.target,
        "rth_only": params.rth_only,
    }

    # Forward request to backend
    return await backend_client.proxy_request(
        method="GET",
        path="/bars/minute_decimated",
        headers=dict(request.headers),
        params=params_dict,
        correlation_id=correlation_id,
    )


@router.get("/bars/hour")
async def proxy_get_hour_bars(
    params: HourBarsQuery = Depends(),
    request: Request = None,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """Proxy GET /bars/hour to backend.

    Gets hourly OHLCV bars for a symbol.
    """
    # Prepare query parameters
    params_dict = {
        "symbol": params.symbol,
        "from": params.from_date,
        "to": params.to_date,
        "rth_only": params.rth_only,
    }

    # Forward request to backend
    return await backend_client.proxy_request(
        method="GET",
        path="/bars/hour",
        headers=dict(request.headers),
        params=params_dict,
        correlation_id=correlation_id,
    )
