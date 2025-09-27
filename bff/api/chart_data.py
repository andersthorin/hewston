"""
Chart Data API

Provides unified chart data aggregation endpoint that combines multiple
backend calls into optimized responses for frontend consumption.
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
import httpx
import logging
import time
from typing import Optional
from datetime import date

from bff.models.chart_data import (
    ChartDataRequest,
    ChartDataResponse,
    ChartDataError,
    TimeframeEnum,
    BarData,
    ResponseMetadata
)
from bff.services.backend_client import BackendClient, create_backend_client
from bff.services.data_transformer import DataTransformer
from bff.services.cache import CacheService
from bff.app.dependencies import get_backend_client, get_redis_client

router = APIRouter()
logger = logging.getLogger("bff.chart_data")


async def get_correlation_id_from_state(request) -> str:
    """Extract correlation ID from request state."""
    return getattr(request.state, 'correlation_id', 'unknown')


@router.get("/chart-data", response_model=ChartDataResponse)
async def get_chart_data(
    symbol: str,
    timeframe: TimeframeEnum,
    from_date: date = Query(..., alias="from"),
    to_date: date = Query(..., alias="to"),
    target_points: int = Query(default=10000, ge=100, le=50000),
    rth_only: bool = Query(default=True),
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
    redis_client = Depends(get_redis_client),
):
    """
    Get unified chart data for a symbol and timeframe.
    
    This endpoint aggregates data from multiple backend endpoints and provides
    optimized responses with caching and data decimation.
    
    Args:
        symbol: Trading symbol (e.g., 'AAPL')
        timeframe: Data timeframe (1D, 1H, 1M, 1M_DECIMATED)
        from_date: Start date for data range
        to_date: End date for data range
        target_points: Target number of data points (for decimation)
        rth_only: Regular trading hours only (for intraday data)
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
            "symbol": symbol,
            "timeframe": timeframe,
            "from_date": str(from_date),
            "to_date": str(to_date),
            "target_points": target_points,
            "rth_only": rth_only,
        }
    )
    
    # Validate request
    try:
        request_data = ChartDataRequest(
            symbol=symbol,
            timeframe=timeframe,
            from_date=from_date,
            to_date=to_date,
            target_points=target_points,
            rth_only=rth_only
        )
    except ValueError as e:
        logger.warning(
            "chart_data.validation_error",
            extra={
                "correlation_id": correlation_id,
                "error": str(e),
                "symbol": symbol,
                "timeframe": timeframe,
            }
        )
        raise HTTPException(status_code=400, detail=str(e))
    
    # Initialize services
    cache_service = CacheService(redis_client)
    data_transformer = DataTransformer()
    backend_proxy = await create_backend_client(backend_client)
    
    # Check cache first
    cache_key = cache_service.generate_chart_cache_key(
        symbol=request_data.symbol,
        timeframe=request_data.timeframe,
        from_date=str(request_data.from_date),
        to_date=str(request_data.to_date),
        target_points=request_data.target_points,
        rth_only=request_data.rth_only
    )
    
    cached_response = await cache_service.get_chart_data(cache_key, correlation_id)
    if cached_response:
        # Update metadata for cache hit
        cached_response.metadata.cache_hit = True
        cached_response.metadata.load_time_ms = int((time.perf_counter() - start_time) * 1000)
        
        logger.info(
            "chart_data.cache_hit",
            extra={
                "correlation_id": correlation_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "bars_count": len(cached_response.bars),
                "load_time_ms": cached_response.metadata.load_time_ms,
            }
        )
        
        return cached_response
    
    # Fetch data from backend
    try:
        backend_data, backend_calls = await _fetch_backend_data(
            backend_proxy,
            request_data,
            correlation_id
        )
        
        if not backend_data:
            raise HTTPException(
                status_code=404,
                detail=f"No data found for {symbol} in timeframe {timeframe}"
            )
        
        # Transform data
        bars = data_transformer.transform_backend_bars(
            backend_data,
            request_data.timeframe,
            correlation_id
        )
        
        # Validate data
        bars = data_transformer.validate_bar_data(bars, correlation_id)
        
        # Apply decimation if needed
        decimated = False
        decimation_stride = 1
        
        if (request_data.timeframe == TimeframeEnum.MINUTE_DECIMATED or 
            len(bars) > request_data.target_points):
            bars, decimation_stride = data_transformer.decimate_data(
                bars,
                request_data.target_points,
                correlation_id
            )
            decimated = decimation_stride > 1
        
        # Determine data source
        data_source = _get_data_source_endpoint(request_data.timeframe)
        
        # Create response
        load_time_ms = int((time.perf_counter() - start_time) * 1000)
        
        response = ChartDataResponse(
            symbol=request_data.symbol,
            timeframe=request_data.timeframe,
            from_date=str(request_data.from_date),
            to_date=str(request_data.to_date),
            bars=bars,
            metadata=ResponseMetadata(
                total_bars=len(bars),
                decimated=decimated,
                decimation_stride=decimation_stride if decimated else None,
                cache_hit=False,
                load_time_ms=load_time_ms,
                backend_calls=backend_calls,
                data_source=data_source
            )
        )
        
        # Cache the response
        ttl = cache_service.calculate_ttl(
            str(request_data.from_date),
            str(request_data.to_date),
            request_data.timeframe
        )
        
        await cache_service.set_chart_data(
            cache_key,
            response,
            ttl,
            correlation_id
        )
        
        logger.info(
            "chart_data.success",
            extra={
                "correlation_id": correlation_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "bars_count": len(bars),
                "decimated": decimated,
                "backend_calls": backend_calls,
                "load_time_ms": load_time_ms,
            }
        )
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "chart_data.error",
            extra={
                "correlation_id": correlation_id,
                "symbol": symbol,
                "timeframe": timeframe,
                "error": str(e),
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal error processing chart data: {str(e)}"
        )


async def _fetch_backend_data(
    backend_client: BackendClient,
    request: ChartDataRequest,
    correlation_id: str
) -> tuple[dict, int]:
    """
    Fetch data from appropriate backend endpoint.
    
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
        method="GET",
        path=endpoint,
        params=params,
        correlation_id=correlation_id
    )
    
    backend_calls += 1
    
    if response.status_code == 200:
        import json
        # Handle both Response objects and mock objects
        if hasattr(response, 'body'):
            response_content = response.body
        else:
            response_content = response.content

        if isinstance(response_content, bytes):
            response_text = response_content.decode('utf-8')
        else:
            response_text = str(response_content)

        return json.loads(response_text), backend_calls
    elif response.status_code == 404:
        return None, backend_calls
    else:
        raise HTTPException(
            status_code=response.status_code,
            detail=f"Backend error: {response.status_code}"
        )


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
