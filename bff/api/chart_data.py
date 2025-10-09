# ruff: noqa: B008

"""Chart Data API.

Provides unified chart data aggregation endpoint that combines multiple backend calls
into optimized responses for frontend consumption.
"""

import logging
import time
from dataclasses import dataclass
from datetime import date
from http import HTTPStatus

import httpx
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse

from bff.app.dependencies import get_backend_client, get_redis_client
from bff.models.chart_data import (
    ChartDataRequest,
    ChartDataResponse,
    ResponseMetadata,
    TimeframeEnum,
)
from bff.services.backend_client import BackendClient, create_backend_client
from bff.services.cache import CacheService, ChartCacheKeyArgs
from bff.services.data_transformer import DataTransformer

router = APIRouter()
logger = logging.getLogger("bff.chart_data")


class ChartQuery:
    """Parsed query params for chart-data using Request for minimal signature."""

    def __init__(self, request: Request) -> None:
        """Initialize from the incoming FastAPI Request's query params.

        Args:
            request: FastAPI request to read query parameters from
        """
        qp = request.query_params
        self.symbol = qp.get("symbol")
        tf = qp.get("timeframe")
        self.timeframe = TimeframeEnum(tf) if tf is not None else None
        f = qp.get("from")
        t = qp.get("to")
        self.from_date = date.fromisoformat(f) if f else None
        self.to_date = date.fromisoformat(t) if t else None
        tp = qp.get("target_points") or qp.get("target")
        self.target_points = int(tp) if tp is not None else 10000
        r = qp.get("rth_only")
        self.rth_only = (str(r).lower() in {"true", "1", "yes"}) if r is not None else True


async def get_correlation_id_from_state(request) -> str:
    """Extract correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")


@router.get("/chart-data", response_model=ChartDataResponse)
async def get_chart_data(
    params: ChartQuery = Depends(),
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
    redis_client=Depends(get_redis_client),
):
    """Get unified chart data for a symbol and timeframe.

    This endpoint aggregates data from multiple backend endpoints and provides
    optimized responses with caching and data decimation.

    Args:
        params: Parsed chart query parameters (symbol, timeframe, from, to, target_points, rth_only)
        backend_client: HTTP client for backend communication
        redis_client: Redis client for caching

    Returns:
        ChartDataResponse: Unified chart data with metadata
    """
    start_time = time.perf_counter()
    correlation_id = f"chart_{int(time.time() * 1000)}"

    logger.info(
        "chart_data.request",
        extra={
            "correlation_id": correlation_id,
            "symbol": params.symbol,
            "timeframe": params.timeframe,
            "from_date": str(params.from_date),
            "to_date": str(params.to_date),
            "target_points": params.target_points,
            "rth_only": params.rth_only,
        },
    )

    # Validate request
    try:
        request_data = ChartDataRequest(
            symbol=params.symbol,
            timeframe=params.timeframe,
            from_date=params.from_date,
            to_date=params.to_date,
            target_points=params.target_points,
            rth_only=params.rth_only,
        )
    except ValueError as e:
        logger.warning(
            "chart_data.validation_error",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "symbol": params.symbol,
                "timeframe": params.timeframe,
            },
        )
        raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail=str(e)) from e

    # Initialize services
    cache_service = CacheService(redis_client)
    data_transformer = DataTransformer()
    backend_proxy = await create_backend_client(backend_client)

    # Check cache first
    cache_key = cache_service.generate_chart_cache_key(
        ChartCacheKeyArgs(
            symbol=request_data.symbol,
            timeframe=request_data.timeframe,
            from_date=str(request_data.from_date),
            to_date=str(request_data.to_date),
            target_points=request_data.target_points,
            rth_only=request_data.rth_only,
        )
    )

    t_cache_get = time.perf_counter()
    cached_response = await cache_service.get_chart_data(cache_key, correlation_id)
    cache_get_ms = int((time.perf_counter() - t_cache_get) * 1000)
    if cached_response:
        # Update metadata for cache hit
        cached_response.metadata.cache_hit = True
        cached_response.metadata.load_time_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "chart_data.cache_hit",
            extra={
                "correlation_id": correlation_id,
                "symbol": params.symbol,
                "timeframe": params.timeframe,
                "bars_count": len(cached_response.bars),
                "cache_get_ms": cache_get_ms,
                "load_time_ms": cached_response.metadata.load_time_ms,
            },
        )

        # Server-Timing for cache hit
        server_timing = (
            f"cache;dur={cache_get_ms}, " f"total;dur={cached_response.metadata.load_time_ms}"
        )
        headers = {"Server-Timing": server_timing}
        return JSONResponse(content=cached_response.model_dump(), headers=headers)

    # Fetch data from backend
    try:
        t_backend_start = time.perf_counter()
        backend_data, backend_calls = await _fetch_backend_data(
            backend_proxy, request_data, correlation_id
        )
        backend_time_ms = int((time.perf_counter() - t_backend_start) * 1000)

        if not backend_data:
            raise HTTPException(
                status_code=HTTPStatus.NOT_FOUND,
                detail=f"No data found for {params.symbol} in timeframe {params.timeframe}",
            )

        # Transform and optionally decimate
        bars, transform_time_ms, decimated, decimation_stride = _transform_and_decimate(
            data_transformer, backend_data, request_data, correlation_id
        )

        # Build response, cache it, and compute headers
        ctx = FinalizeContext(
            bars=bars,
            decimated=decimated,
            decimation_stride=decimation_stride,
            backend_calls=backend_calls,
            backend_time_ms=backend_time_ms,
            transform_time_ms=transform_time_ms,
            cache_get_ms=cache_get_ms,
            start_time=start_time,
        )
        response_dict, headers, cache_set_ms = await _finalize_and_cache(
            cache_service,
            request_data,
            ctx,
            correlation_id,
        )

        # Logging
        load_time_ms = int((time.perf_counter() - start_time) * 1000)
        logger.info(
            "chart_data.success",
            extra={
                "correlation_id": correlation_id,
                "symbol": params.symbol,
                "timeframe": params.timeframe,
                "bars_count": len(bars),
                "decimated": decimated,
                "backend_calls": backend_calls,
                "load_time_ms": load_time_ms,
                "backend_time_ms": backend_time_ms,
                "transform_time_ms": transform_time_ms,
                "cache_get_ms": cache_get_ms,
                "cache_set_ms": cache_set_ms,
            },
        )

        return JSONResponse(content=response_dict, headers=headers)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "chart_data.error",
            extra={
                "correlation_id": correlation_id,
                "symbol": params.symbol,
                "timeframe": params.timeframe,
                "error": str(e),
            },
        )

        raise HTTPException(
            status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
            detail=f"Internal error processing chart data: {str(e)}",
        ) from e


async def _fetch_backend_data(
    backend_client: BackendClient, request: ChartDataRequest, correlation_id: str
) -> tuple[dict, int]:
    """Fetch data from appropriate backend endpoint.

    Args:
        backend_client: Backend HTTP client
        request: Chart data request
        correlation_id: Request correlation ID

    Returns:
        tuple[dict, int]: (backend_data, backend_calls_count)
    """
    backend_calls = 0

    # Determine backend endpoint based on timeframe
    if request.timeframe == TimeframeEnum.DAILY:
        endpoint = "/bars/daily"
        params = {
            "symbol": request.symbol,
            "from": str(request.from_date),
            "to": str(request.to_date),
        }
    elif request.timeframe == TimeframeEnum.HOURLY:
        endpoint = "/bars/hour"
        params = {
            "symbol": request.symbol,
            "from": str(request.from_date),
            "to": str(request.to_date),
            "rth_only": request.rth_only,
        }
    elif request.timeframe in [TimeframeEnum.MINUTE, TimeframeEnum.MINUTE_DECIMATED]:
        if request.timeframe == TimeframeEnum.MINUTE_DECIMATED:
            endpoint = "/bars/minute_decimated"
            params = {
                "symbol": request.symbol,
                "from": str(request.from_date),
                "to": str(request.to_date),
                "target": request.target_points,
                "rth_only": request.rth_only,
            }
        else:
            endpoint = "/bars/minute"
            params = {
                "symbol": request.symbol,
                "from": str(request.from_date),
                "to": str(request.to_date),
                "rth_only": request.rth_only,
            }
    else:
        raise ValueError(f"Unsupported timeframe: {request.timeframe}")

    # Make backend request
    response = await backend_client.proxy_request(
        method="GET", path=endpoint, params=params, correlation_id=correlation_id
    )

    backend_calls += 1

    if response.status_code == HTTPStatus.OK:
        import json

        # Handle both Response objects and mock objects
        response_content = response.body if hasattr(response, "body") else response.content

        if isinstance(response_content, bytes):
            response_text = response_content.decode("utf-8")
        else:
            response_text = str(response_content)

        return json.loads(response_text), backend_calls
    elif response.status_code == HTTPStatus.NOT_FOUND:
        return None, backend_calls
    else:
        raise HTTPException(
            status_code=response.status_code, detail=f"Backend error: {response.status_code}"
        )


def _transform_and_decimate(
    transformer: DataTransformer,
    backend_data: dict,
    request: ChartDataRequest,
    correlation_id: str,
) -> tuple[list[dict], int, bool, int]:
    """Transform backend data to bars and apply decimation if needed.

    Returns:
        (bars, transform_time_ms, decimated, decimation_stride)
    """
    t_transform_start = time.perf_counter()
    bars = transformer.transform_backend_bars(backend_data, request.timeframe, correlation_id)
    bars = transformer.validate_bar_data(bars, correlation_id)
    transform_time_ms = int((time.perf_counter() - t_transform_start) * 1000)

    decimated = False
    decimation_stride = 1
    if request.timeframe == TimeframeEnum.MINUTE_DECIMATED or len(bars) > request.target_points:
        bars, decimation_stride = transformer.decimate_data(
            bars, request.target_points, correlation_id
        )
        decimated = decimation_stride > 1

    return bars, transform_time_ms, decimated, decimation_stride


@dataclass
class FinalizeContext:
    """Context container for finalize-and-cache step."""

    bars: list[dict]
    decimated: bool
    decimation_stride: int
    backend_calls: int
    backend_time_ms: int
    transform_time_ms: int
    cache_get_ms: int
    start_time: float


async def _finalize_and_cache(
    cache: CacheService,
    request: ChartDataRequest,
    ctx: FinalizeContext,
    correlation_id: str,
) -> tuple[dict, dict, int]:
    """Build response model, cache it, and compute headers.

    Returns:
        (response_dict, headers, cache_set_ms)
    """
    data_source = _get_data_source_endpoint(request.timeframe)
    load_time_ms = int((time.perf_counter() - ctx.start_time) * 1000)

    response = ChartDataResponse(
        symbol=request.symbol,
        timeframe=request.timeframe,
        from_date=str(request.from_date),
        to_date=str(request.to_date),
        bars=ctx.bars,
        metadata=ResponseMetadata(
            total_bars=len(ctx.bars),
            decimated=ctx.decimated,
            decimation_stride=ctx.decimation_stride if ctx.decimated else None,
            cache_hit=False,
            load_time_ms=load_time_ms,
            backend_calls=ctx.backend_calls,
            data_source=data_source,
        ),
    )

    ttl = cache.calculate_ttl(str(request.from_date), str(request.to_date), request.timeframe)
    cache_key = cache.generate_chart_cache_key(
        ChartCacheKeyArgs(
            symbol=request.symbol,
            timeframe=request.timeframe,
            from_date=str(request.from_date),
            to_date=str(request.to_date),
            target_points=request.target_points,
            rth_only=request.rth_only,
        )
    )

    t_cache_set = time.perf_counter()
    await cache.set_chart_data(cache_key, response, ttl, correlation_id)
    cache_set_ms = int((time.perf_counter() - t_cache_set) * 1000)

    server_timing = (
        f"backend;dur={ctx.backend_time_ms}, "
        f"transform;dur={ctx.transform_time_ms}, "
        f"cache_get;dur={ctx.cache_get_ms}, "
        f"cache_set;dur={cache_set_ms}, "
        f"total;dur={load_time_ms}"
    )
    headers = {"Server-Timing": server_timing}

    return response.model_dump(), headers, cache_set_ms


def _get_data_source_endpoint(timeframe: TimeframeEnum) -> str:
    """Get the backend endpoint name for a timeframe."""
    if timeframe == TimeframeEnum.DAILY:
        return "/bars/daily"
    elif timeframe == TimeframeEnum.HOURLY:
        return "/bars/hour"
    elif timeframe == TimeframeEnum.MINUTE:
        return "/bars/minute"
    elif timeframe == TimeframeEnum.MINUTE_DECIMATED:
        return "/bars/minute_decimated"
    else:
        return "unknown"
