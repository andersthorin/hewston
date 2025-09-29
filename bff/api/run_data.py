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
from typing import Dict, Any, List

router = APIRouter()
logger = logging.getLogger("bff.run_data")


async def get_correlation_id_from_state(request) -> str:
    """Extract correlation ID from request state."""
    return getattr(request.state, 'correlation_id', 'unknown')


@router.get("/runs")
async def list_runs(
    limit: int = Query(default=20, description="Maximum number of runs to return"),
    offset: int = Query(default=0, description="Number of runs to skip"),
    symbol: Optional[str] = Query(default=None, description="Filter by trading symbol"),
    strategy_id: Optional[str] = Query(default=None, description="Filter by strategy ID"),
    from_date: Optional[str] = Query(default=None, alias="from", description="Filter runs from this date"),
    to_date: Optional[str] = Query(default=None, alias="to", description="Filter runs to this date"),
    order: Optional[str] = Query(default=None, description="Sort order (created_at, -created_at)"),
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
    redis_client = Depends(get_redis_client),
) -> Dict[str, Any]:
    """
    List runs with filtering and pagination.

    This endpoint provides a unified interface for listing runs with the same
    parameters as the backend /backtests endpoint, but with BFF enhancements
    like caching and response optimization.

    Args:
        limit: Maximum number of runs to return (1-500, default 20)
        offset: Number of runs to skip for pagination (default 0)
        symbol: Filter by trading symbol (optional)
        strategy_id: Filter by strategy identifier (optional)
        from_date: Filter runs created from this date (optional)
        to_date: Filter runs created to this date (optional)
        order: Sort order - 'created_at' or '-created_at' (default -created_at)
        backend_client: HTTP client for backend communication
        redis_client: Redis client for caching

    Returns:
        Dict containing:
        - items: List of run summaries
        - total: Total number of matching runs
        - limit: Applied limit
        - offset: Applied offset
        - meta: Response metadata (cache info, performance metrics)
    """
    start_time = time.perf_counter()
    correlation_id = f"list_runs_{int(time.time() * 1000)}"

    logger.info(
        "list_runs.request",
        extra={
            "correlation_id": correlation_id,
            "limit": limit,
            "offset": offset,
            "symbol": symbol,
            "strategy_id": strategy_id,
            "from_date": from_date,
            "to_date": to_date,
            "order": order,
        }
    )

    # Validate and sanitize parameters
    limit = max(1, min(int(limit), 500))
    offset = max(0, int(offset))
    allowed_orders = {"created_at", "-created_at"}
    order = order if order in allowed_orders else "-created_at"

    # Build query parameters for backend
    params = {
        "limit": limit,
        "offset": offset,
    }
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

    # For now, skip caching for run lists (can be added later)
    # Run lists change frequently and caching complexity isn't worth it for this endpoint

    # Fetch from backend
    try:
        backend_proxy = await create_backend_client(backend_client)
        response = await backend_proxy.proxy_request(
            method="GET",
            path="/backtests",
            params=params,
            correlation_id=correlation_id
        )

        # Parse JSON response
        if hasattr(response, 'json') and callable(response.json):
            backend_data = response.json()
        else:
            # Handle FastAPI Response object
            import json
            backend_data = json.loads(response.body.decode())

        # Add BFF metadata
        load_time_ms = int((time.perf_counter() - start_time) * 1000)
        enhanced_response = {
            **backend_data,
            "meta": {
                "cache_hit": False,
                "load_time_ms": load_time_ms,
                "source": "bff",
                "backend_calls": 1,
            }
        }

        # Skip caching for now - can be added later if needed

        logger.info(
            "list_runs.success",
            extra={
                "correlation_id": correlation_id,
                "items_count": len(enhanced_response.get("items", [])),
                "total": enhanced_response.get("total", 0),
                "load_time_ms": load_time_ms,
            }
        )

        return enhanced_response

    except Exception as e:
        # Handle both httpx errors and FastAPI response errors
        status_code = getattr(e, 'status_code', 500)
        if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
            status_code = e.response.status_code

        logger.error(
            "list_runs.backend_error",
            extra={
                "correlation_id": correlation_id,
                "status_code": status_code,
                "error": str(e),
                "error_type": type(e).__name__,
            }
        )

        if status_code != 500:
            raise HTTPException(
                status_code=status_code,
                detail=f"Backend error: {status_code}"
            )
        else:
            raise HTTPException(
                status_code=500,
                detail="Internal server error while fetching runs"
            )


@router.get("/runs/{run_id}/complete")
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

        # Transform to frontend contract while keeping backward-compatible fields
        metrics_dict = None
        if cached_response.metrics is not None:
            md = cached_response.metrics.dict()
            metrics_dict = {k: v for k, v in md.items() if v is not None}
            if not metrics_dict:
                metrics_dict = None
        equity_list = (
            [{"ts": p.ts, "value": p.value} for p in (cached_response.equity or [])]
            if cached_response.equity else None
        )
        orders_list = (
            [
                {
                    "ts": o.ts,
                    "side": o.side,
                    "quantity": o.quantity,
                    "price": o.price,
                    "order_type": o.order_type,
                    "status": o.status,
                }
                for o in (cached_response.orders or [])
            ] if cached_response.orders else None
        )
        # Determine run window and dataset
        run_from_val = getattr(cached_response.run, "run_from", None)
        run_to_val = getattr(cached_response.run, "run_to", None)
        if (not run_from_val or not run_to_val) and equity_list and len(equity_list) > 0:
            try:
                run_from_val = run_from_val or equity_list[0]["ts"]
                run_to_val = run_to_val or equity_list[-1]["ts"]
            except Exception:
                pass
        dataset_id_val = getattr(cached_response.run, "dataset_id", None)

        frontend_payload = {
            # Top-level fields expected by frontend schema
            "run_id": cached_response.run.run_id,
            "strategy_id": cached_response.run.strategy_id,
            "status": cached_response.run.status,
            "symbol": cached_response.run.symbol,
            "params": cached_response.run.params or {},
            # Preferred naming per app memory (run_from/run_to)
            "run_from": run_from_val,
            "run_to": run_to_val,
            # Optional fields
            "dataset_id": dataset_id_val,
            "code_hash": None,
            "seed": None,
            "speed": None,
            "duration_ms": None,
            # Aggregated data
            "metrics": metrics_dict,
            "equity": equity_list,
            "orders": orders_list,
            # Meta block for BFF
            "meta": {
                "aggregated": True,
                "cache_hit": cached_response.metadata.cache_hit,
                "load_time_ms": cached_response.metadata.load_time_ms,
                "source": "bff",
                "components_loaded": [
                    name for name, val in (
                        ("metrics", cached_response.metrics),
                        ("equity", cached_response.equity),
                        ("orders", cached_response.orders),
                    ) if val
                ],
            },
            # Backward-compatible fields (to avoid breaking existing tests/tools)
            "run": cached_response.run.dict(),
            "metadata": cached_response.metadata.dict(),
        }
        return JSONResponse(status_code=200, content=frontend_payload)

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

        # Transform to frontend contract while keeping backward-compatible fields
        metrics_dict = None
        if response.metrics is not None:
            md = response.metrics.dict()
            metrics_dict = {k: v for k, v in md.items() if v is not None}
            if not metrics_dict:
                metrics_dict = None
        equity_list = (
            [{"ts": p.ts, "value": p.value} for p in (response.equity or [])]
            if response.equity else None
        )
        orders_list = (
            [
                {
                    "ts": o.ts,
                    "side": o.side,
                    "quantity": o.quantity,
                    "price": o.price,
                    "order_type": o.order_type,
                    "status": o.status,
                }
                for o in (response.orders or [])
            ] if response.orders else None
        )
        # Determine run window and dataset
        run_from_val = getattr(response.run, "run_from", None)
        run_to_val = getattr(response.run, "run_to", None)
        if (not run_from_val or not run_to_val) and equity_list and len(equity_list) > 0:
            try:
                run_from_val = run_from_val or equity_list[0]["ts"]
                run_to_val = run_to_val or equity_list[-1]["ts"]
            except Exception:
                pass
        dataset_id_val = getattr(response.run, "dataset_id", None)

        frontend_payload = {
            # Top-level fields expected by frontend schema
            "run_id": response.run.run_id,
            "strategy_id": response.run.strategy_id,
            "status": response.run.status,
            "symbol": response.run.symbol,
            "params": response.run.params or {},
            # Preferred naming per app memory (run_from/run_to)
            "run_from": run_from_val,
            "run_to": run_to_val,
            # Optional fields
            "dataset_id": dataset_id_val,
            "code_hash": None,
            "seed": None,
            "speed": None,
            "duration_ms": None,
            # Aggregated data
            "metrics": metrics_dict,
            "equity": equity_list,
            "orders": orders_list,
            # Meta block for BFF
            "meta": {
                "aggregated": True,
                "cache_hit": response.metadata.cache_hit,
                "load_time_ms": response.metadata.load_time_ms,
                "source": "bff",
                "components_loaded": [
                    name for name, val in (
                        ("metrics", response.metrics),
                        ("equity", response.equity),
                        ("orders", response.orders),
                    ) if val
                ],
            },
            # Backward-compatible fields (to avoid breaking existing tests/tools)
            "run": response.run.dict(),
            "metadata": response.metadata.dict(),
        }
        return JSONResponse(status_code=200, content=frontend_payload)

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
