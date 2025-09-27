"""
Run Data API

Provides unified run data aggregation endpoint that combines multiple
backend calls into optimized responses for frontend consumption.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
import httpx
import logging
import time
from typing import Optional

from bff.models.run_data import (
    CompleteRunResponse,
    RunDataRequest,
    RunDataError
)
from bff.services.backend_client import BackendClient, create_backend_client
from bff.services.run_aggregator import RunDataAggregator
from bff.services.cache import CacheService
from bff.app.dependencies import get_backend_client, get_redis_client

router = APIRouter()
logger = logging.getLogger("bff.run_data")


async def get_correlation_id_from_state(request) -> str:
    """Extract correlation ID from request state."""
    return getattr(request.state, 'correlation_id', 'unknown')


@router.get("/runs/{run_id}/complete", response_model=CompleteRunResponse)
async def get_complete_run_data(
    run_id: str = Path(..., description="Run identifier"),
    include_orders: bool = Query(default=True, description="Include order execution data"),
    include_equity: bool = Query(default=True, description="Include equity curve data"),
    include_metrics: bool = Query(default=True, description="Include performance metrics"),
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
    redis_client = Depends(get_redis_client),
):
    """
    Get complete aggregated run data.
    
    This endpoint aggregates data from multiple backend endpoints and provides
    optimized responses with caching and concurrent data fetching.
    
    Args:
        run_id: Unique run identifier
        include_orders: Whether to include order execution data
        include_equity: Whether to include equity curve data
        include_metrics: Whether to include performance metrics
        backend_client: HTTP client for backend communication
        redis_client: Redis client for caching
        
    Returns:
        CompleteRunResponse: Aggregated run data with metadata
    """
    start_time = time.perf_counter()
    correlation_id = f"run_{run_id}_{int(time.time() * 1000)}"
    
    logger.info(
        "run_data.request",
        extra={
            "correlation_id": correlation_id,
            "run_id": run_id,
            "include_orders": include_orders,
            "include_equity": include_equity,
            "include_metrics": include_metrics,
        }
    )
    
    # Validate run_id format
    if not run_id or not run_id.strip():
        logger.warning(
            "run_data.validation_error",
            extra={
                "correlation_id": correlation_id,
                "error": "empty_run_id",
                "run_id": run_id,
            }
        )
        raise HTTPException(status_code=400, detail="Run ID cannot be empty")
    
    # Create request parameters
    request_params = RunDataRequest(
        include_orders=include_orders,
        include_equity=include_equity,
        include_metrics=include_metrics
    )
    
    # Initialize services
    cache_service = CacheService(redis_client)
    aggregator = RunDataAggregator()
    backend_proxy = await create_backend_client(backend_client)
    
    # Check cache first
    cache_key = cache_service.generate_run_cache_key(
        run_id=run_id,
        include_orders=include_orders,
        include_equity=include_equity,
        include_metrics=include_metrics
    )
    
    cached_response = await cache_service.get_run_data(cache_key, correlation_id)
    if cached_response:
        # Update metadata for cache hit
        cached_response.metadata.cache_hit = True
        cached_response.metadata.load_time_ms = int((time.perf_counter() - start_time) * 1000)
        
        logger.info(
            "run_data.cache_hit",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "load_time_ms": cached_response.metadata.load_time_ms,
            }
        )
        
        return cached_response
    
    # Aggregate data from backend
    try:
        response = await aggregator.aggregate_run_data(
            run_id=run_id,
            backend_client=backend_proxy,
            request_params=request_params,
            correlation_id=correlation_id
        )
        
        # Cache the response if run is completed
        if response.run.status in ["COMPLETED", "FAILED"]:
            # Use longer TTL for completed runs
            ttl = 3600  # 1 hour for completed runs
            await cache_service.set_run_data(
                cache_key,
                response,
                ttl,
                correlation_id
            )
        elif response.run.status == "RUNNING":
            # Short TTL for running runs
            ttl = 60  # 1 minute for running runs
            await cache_service.set_run_data(
                cache_key,
                response,
                ttl,
                correlation_id
            )
        # Don't cache queued runs
        
        logger.info(
            "run_data.success",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "status": response.run.status,
                "load_time_ms": response.metadata.load_time_ms,
                "backend_calls": response.metadata.backend_calls,
                "partial_data": response.metadata.partial_data,
            }
        )
        
        return response
        
    except ValueError as e:
        # Run not found
        logger.warning(
            "run_data.not_found",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "error": str(e),
            }
        )
        raise HTTPException(status_code=404, detail=str(e))
        
    except Exception as e:
        logger.exception(
            "run_data.error",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "error": str(e),
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal error processing run data: {str(e)}"
        )


@router.get("/runs/{run_id}/status")
async def get_run_status(
    run_id: str = Path(..., description="Run identifier"),
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
):
    """
    Get run status only (lightweight endpoint).
    
    This endpoint provides just the run status and basic details
    without fetching metrics, equity, or order data.
    
    Args:
        run_id: Unique run identifier
        backend_client: HTTP client for backend communication
        
    Returns:
        Dict: Run status and basic details
    """
    correlation_id = f"status_{run_id}_{int(time.time() * 1000)}"
    
    logger.info(
        "run_status.request",
        extra={
            "correlation_id": correlation_id,
            "run_id": run_id,
        }
    )
    
    try:
        backend_proxy = await create_backend_client(backend_client)
        
        response = await backend_proxy.proxy_request(
            method="GET",
            path=f"/backtests/{run_id}",
            correlation_id=correlation_id
        )
        
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

            data = json.loads(response_text)
            
            # Return lightweight status response
            status_response = {
                "run_id": data.get("run_id"),
                "status": data.get("status"),
                "strategy_id": data.get("strategy_id"),
                "symbol": data.get("symbol"),
                "created_at": data.get("created_at"),
                "started_at": data.get("started_at"),
                "completed_at": data.get("completed_at"),
                "error_message": data.get("error_message")
            }
            
            logger.info(
                "run_status.success",
                extra={
                    "correlation_id": correlation_id,
                    "run_id": run_id,
                    "status": status_response["status"],
                }
            )
            
            return status_response
            
        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Run {run_id} not found")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Backend error: {response.status_code}"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "run_status.error",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "error": str(e),
            }
        )
        
        raise HTTPException(
            status_code=500,
            detail=f"Internal error getting run status: {str(e)}"
        )
