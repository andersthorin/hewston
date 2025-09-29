"""
Backtests API

Provides unified backtest data aggregation endpoints that combine multiple
backend calls into optimized responses for frontend consumption.
"""

from fastapi import APIRouter, Depends, HTTPException, Query, Path
from fastapi.responses import JSONResponse
import httpx
import logging
import time
from typing import Optional

from bff.models.backtest_data import (
    CompleteBacktestResponse,
    BacktestDataRequest,
    BacktestDataError,
)
from bff.services.backend_client import BackendClient, create_backend_client
from bff.services.backtest_aggregator import BacktestDataAggregator
from bff.services.cache import CacheService
from bff.app.dependencies import get_backend_client, get_redis_client
from typing import Dict, Any, List

router = APIRouter()
logger = logging.getLogger("bff.backtests_api")


async def get_correlation_id_from_state(request) -> str:
    """Extract correlation ID from request state."""
    return getattr(request.state, 'correlation_id', 'unknown')


@router.post("/backtests")
async def create_backtest_via_bff(
    request: Any,
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
):
    """
    Create a backtest via BFF domain endpoint.

    Frontend sends POST /api/v1/backtests; this forwards to backend /backtests
    while preserving headers (including Idempotency-Key) and body.
    """
    try:
        backend_proxy = await create_backend_client(backend_client)
        raw_body = await request.body()
        headers = dict(request.headers)

        # Parse and normalize simplified UI payload → backend payload
        import json as _json
        try:
            incoming = _json.loads(raw_body.decode("utf-8") or "{}") if isinstance(raw_body, (bytes, bytearray)) else {}
            if not isinstance(incoming, dict):
                incoming = {}
        except Exception:
            incoming = {}

        strategy_id = incoming.get("strategy_id")
        symbol = incoming.get("symbol")
        # Prefer canonical run_from/run_to if provided, fallback to from/to
        run_from = incoming.get("run_from") or incoming.get("from")
        run_to = incoming.get("run_to") or incoming.get("to")

        mapped: Dict[str, Any] = {}
        if strategy_id:
            mapped["strategy_id"] = strategy_id
        if symbol:
            mapped["symbol"] = symbol
        if run_from:
            mapped["from"] = run_from
        if run_to:
            mapped["to"] = run_to
        # Pass-through dataset_id if caller provided it (not in simplified form)
        if isinstance(incoming.get("dataset_id"), str) and incoming.get("dataset_id"):
            mapped["dataset_id"] = incoming["dataset_id"]

        # If caller provided symbol without dataset_id, backend expects (symbol, year)
        # Derive year from run_from (or run_to) to avoid backend stub IDs
        if symbol and "dataset_id" not in mapped and not incoming.get("year"):
            year_src = (run_from or run_to or "").strip()
            # Accept ISO date formats like YYYY-MM-DD or full timestamps
            if len(year_src) >= 4 and year_src[:4].isdigit():
                try:
                    mapped["year"] = int(year_src[:4])
                except Exception:
                    pass

        # Defaults for removed fields: params, speed, seed
        if isinstance(incoming.get("params"), dict):
            mapped["params"] = incoming["params"]
        else:
            if strategy_id == "sma_crossover":
                mapped["params"] = {"fast": 20, "slow": 50}
            else:
                mapped["params"] = {}
        mapped["speed"] = int(incoming.get("speed") or 60)
        mapped["seed"] = int(incoming.get("seed") or 42)
        if isinstance(incoming.get("slippage_fees"), dict):
            mapped["slippage_fees"] = incoming["slippage_fees"]

        response = await backend_proxy.proxy_request(
            method="POST",
            path="/backtests",
            headers=headers,
            json_data=mapped,
            correlation_id=getattr(request.state, "correlation_id", "create_backtest"),
        )
        # Transform backend response to canonical backtest_id-only payload
        data: Dict[str, Any] | None = None
        # Prefer reading FastAPI JSONResponse body when available
        if hasattr(response, 'body'):
            try:
                raw = response.body.decode()  # type: ignore[attr-defined]
                data = _json.loads(raw or "{}")
            except Exception:
                data = None
        # Fallback to response.json() if provided
        # Log mapped payload and backend response for debugging (info level)
        try:
            logger.info("bff.create_backtest.response", extra={"mapped": mapped, "status_code": getattr(response, 'status_code', None)})
        except Exception:
            pass
        if data is None and hasattr(response, 'json'):
            try:
                data = response.json()  # type: ignore[call-arg]
            except Exception:
                data = None
        if not isinstance(data, dict):
            data = {}
        transformed = {
            "backtest_id": data.get("run_id") or data.get("backtest_id"),
            "status": data.get("status"),
        }
        return JSONResponse(status_code=response.status_code, content=transformed)
    except httpx.HTTPStatusError as e:
        raise HTTPException(status_code=e.response.status_code, detail=str(e))
    except Exception as e:
        logger.exception("create_backtest.error", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Internal error creating backtest")



@router.get("/backtests")
async def list_backtests(
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
    List backtests with filtering and pagination.

    Canonical backtests endpoint with BFF enhancements like caching and
    response optimization.

    Args:
        limit: Maximum number of backtests to return (1-500, default 20)
        offset: Number of backtests to skip (default 0)
        symbol: Filter by trading symbol (optional)
        strategy_id: Filter by strategy identifier (optional)
        from_date: Filter created from this date (optional)
        to_date: Filter created to this date (optional)
        order: Sort order - 'created_at' or '-created_at' (default -created_at)

    Returns:
        Dict containing:
        - items: List of backtest summaries
        - total: Total number of matching backtests
        - limit: Applied limit
        - offset: Applied offset
        - meta: Response metadata (cache info, performance metrics)
    """
    start_time = time.perf_counter()
    correlation_id = f"list_backtests_{int(time.time() * 1000)}"

    logger.info(
        "list_backtests.request",
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

    # Skip caching for now

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
            import json
            backend_data = json.loads(response.body.decode())

        # Transform items to backtest_id-only identifiers (robust to backend shapes)
        items = backend_data.get("items", []) or []
        new_items = []
        for item in items:
            run_obj = item.get("run") if isinstance(item, dict) else None
            bt_id = (
                (item.get("backtest_id") if isinstance(item, dict) else None)
                or (item.get("run_id") if isinstance(item, dict) else None)
                or (item.get("id") if isinstance(item, dict) else None)
                or ((run_obj or {}).get("run_id") if isinstance(run_obj, dict) else None)
                or ((run_obj or {}).get("id") if isinstance(run_obj, dict) else None)
            )
            created_at = (
                (item.get("created_at") if isinstance(item, dict) else None)
                or ((run_obj or {}).get("created_at") if isinstance(run_obj, dict) else None)
                or (item.get("createdAt") if isinstance(item, dict) else None)
            )
            strategy_id = (
                (item.get("strategy_id") if isinstance(item, dict) else None)
                or ((run_obj or {}).get("strategy_id") if isinstance(run_obj, dict) else None)
                or (item.get("strategyId") if isinstance(item, dict) else None)
            )
            status = (
                (item.get("status") if isinstance(item, dict) else None)
                or ((run_obj or {}).get("status") if isinstance(run_obj, dict) else None)
            )
            symbol = (
                (item.get("symbol") if isinstance(item, dict) else None)
                or ((run_obj or {}).get("symbol") if isinstance(run_obj, dict) else None)
            )
            run_from = (
                (item.get("run_from") if isinstance(item, dict) else None)
                or (item.get("from_date") if isinstance(item, dict) else None)
                or ((run_obj or {}).get("run_from") if isinstance(run_obj, dict) else None)
                or ((run_obj or {}).get("from_date") if isinstance(run_obj, dict) else None)
            )
            run_to = (
                (item.get("run_to") if isinstance(item, dict) else None)
                or (item.get("to_date") if isinstance(item, dict) else None)
                or ((run_obj or {}).get("run_to") if isinstance(run_obj, dict) else None)
                or ((run_obj or {}).get("to_date") if isinstance(run_obj, dict) else None)
            )
            duration_ms = (
                (item.get("duration_ms") if isinstance(item, dict) else None)
                or ((run_obj or {}).get("duration_ms") if isinstance(run_obj, dict) else None)
                or (item.get("durationMs") if isinstance(item, dict) else None)
            )
            new_items.append({
                "backtest_id": bt_id,
                "created_at": created_at,
                "strategy_id": strategy_id,
                "status": status,
                "symbol": symbol,
                "run_from": run_from,
                "run_to": run_to,
                "duration_ms": duration_ms,
                "total_return": item.get("total_return") if isinstance(item, dict) else None,
                "sharpe_ratio": item.get("sharpe_ratio") if isinstance(item, dict) else None,
                "max_drawdown": item.get("max_drawdown") if isinstance(item, dict) else None,
            })

        load_time_ms = int((time.perf_counter() - start_time) * 1000)
        enhanced_response = {
            "items": new_items,
            "total": backend_data.get("total", len(new_items)),
            "limit": backend_data.get("limit", limit),
            "offset": backend_data.get("offset", offset),
            "meta": {
                "cache_hit": False,
                "load_time_ms": load_time_ms,
                "source": "bff",
                "backend_calls": 1,
            }
        }

        logger.info(
            "list_backtests.success",
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
            "list_backtests.backend_error",
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
                detail="Internal server error while fetching backtests"
            )


@router.get("/backtests/{backtest_id}/complete")
async def get_complete_backtest_data(
    backtest_id: str = Path(..., description="Backtest identifier"),
    include_orders: bool = Query(default=True, description="Include order execution data"),
    include_equity: bool = Query(default=True, description="Include equity curve data"),
    include_metrics: bool = Query(default=True, description="Include performance metrics"),
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
    redis_client = Depends(get_redis_client),
):
    # Normalize local variable name for downstream logic
    run_id = backtest_id

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
        "backtests.request",
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
        raise HTTPException(status_code=400, detail="Backtest ID cannot be empty")

    # Create request parameters
    request_params = BacktestDataRequest(
        include_orders=include_orders,
        include_equity=include_equity,
        include_metrics=include_metrics
    )

    # Initialize services
    cache_service = CacheService(redis_client)
    aggregator = BacktestDataAggregator()
    backend_proxy = await create_backend_client(backend_client)

    # Check cache first
    cache_key = cache_service.generate_backtest_cache_key(
        run_id=run_id,
        include_orders=include_orders,
        include_equity=include_equity,
        include_metrics=include_metrics
    )

    cached_response = await cache_service.get_backtest_data(cache_key, correlation_id)
    if cached_response:
        # Update metadata for cache hit
        cached_response.metadata.cache_hit = True
        cached_response.metadata.load_time_ms = int((time.perf_counter() - start_time) * 1000)

        logger.info(
            "backtests.cache_hit",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "load_time_ms": cached_response.metadata.load_time_ms,
            }
        )

        # Transform to frontend contract while keeping backward-compatible fields
        metrics_dict = None
        if cached_response.metrics is not None:
            md = cached_response.metrics.model_dump()
            metrics_dict = {k: v for k, v in md.items() if v is not None}
            if not metrics_dict:
                metrics_dict = None
        equity_list = None
        if cached_response.equity is not None:
            equity_list = [{"ts": p.ts, "value": p.value} for p in cached_response.equity]
        orders_list = None
        if cached_response.orders is not None:
            orders_list = [
                {
                    "order_id": getattr(o, "order_id", None) or getattr(o, "id", None),
                    "timestamp": o.ts,
                    "symbol": getattr(o, "symbol", None),
                    "side": o.side,
                    "quantity": o.quantity,
                    "price": o.price,
                    "order_type": o.order_type,
                    "status": o.status,
                }
                for o in cached_response.orders
            ]
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
            "run": {
                "run_id": cached_response.run.run_id,
                "strategy_id": cached_response.run.strategy_id,
                "status": cached_response.run.status,
                "symbol": cached_response.run.symbol,
                "params": cached_response.run.params or {},
                "run_from": run_from_val,
                "run_to": run_to_val,
                "dataset_id": dataset_id_val,
            },
            "metrics": metrics_dict,
            "equity": equity_list,
            "orders": orders_list,
            "metadata": {
                "load_time_ms": cached_response.metadata.load_time_ms,
                "cache_hit": cached_response.metadata.cache_hit,
                "backend_calls": cached_response.metadata.backend_calls,
                "data_sources": cached_response.metadata.data_sources,
                "partial_data": cached_response.metadata.partial_data,
                "failed_sources": cached_response.metadata.failed_sources,
                "orders_count": cached_response.metadata.orders_count,
                "equity_points": cached_response.metadata.equity_points,
            },
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
            await cache_service.set_backtest_data(
                cache_key,
                response,
                ttl,
                correlation_id
            )
        elif response.run.status == "RUNNING":
            # Short TTL for running runs
            ttl = 60  # 1 minute for running runs
            await cache_service.set_backtest_data(
                cache_key,
                response,
                ttl,
                correlation_id
            )
        # Don't cache queued runs

        logger.info(
            "backtests.success",
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
            md = response.metrics.model_dump()
            metrics_dict = {k: v for k, v in md.items() if v is not None}
            if not metrics_dict:
                metrics_dict = None
        equity_list = None
        if response.equity is not None:
            equity_list = [{"ts": p.ts, "value": p.value} for p in response.equity]
        orders_list = None
        if response.orders is not None:
            orders_list = [
                {
                    "order_id": getattr(o, "order_id", None) or getattr(o, "id", None),
                    "timestamp": o.ts,
                    "symbol": getattr(o, "symbol", None),
                    "side": o.side,
                    "quantity": o.quantity,
                    "price": o.price,
                    "order_type": o.order_type,
                    "status": o.status,
                }
                for o in response.orders
            ]
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
            "run": {
                "run_id": response.run.run_id,
                "strategy_id": response.run.strategy_id,
                "status": response.run.status,
                "symbol": response.run.symbol,
                "params": response.run.params or {},
                "run_from": run_from_val,
                "run_to": run_to_val,
                "dataset_id": dataset_id_val,
            },
            "metrics": metrics_dict,
            "equity": equity_list,
            "orders": orders_list,
            "metadata": {
                "load_time_ms": response.metadata.load_time_ms,
                "cache_hit": response.metadata.cache_hit,
                "backend_calls": response.metadata.backend_calls,
                "data_sources": response.metadata.data_sources,
                "partial_data": response.metadata.partial_data,
                "failed_sources": response.metadata.failed_sources,
                "orders_count": response.metadata.orders_count,
                "equity_points": response.metadata.equity_points,
            },
        }
        return JSONResponse(status_code=200, content=frontend_payload)

    except ValueError as e:
        # Run not found
        logger.warning(
            "backtests.not_found",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "error": str(e),
            }
        )
        raise HTTPException(status_code=404, detail=str(e))

    except Exception as e:
        logger.exception(
            "backtests.error",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "error": str(e),
            }
        )

        raise HTTPException(
            status_code=500,
            detail=f"Internal error processing backtest data: {str(e)}"
        )


@router.get("/backtests/{backtest_id}/status")
async def get_backtest_status(
    backtest_id: str = Path(..., description="Backtest identifier"),
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
):
    run_id = backtest_id
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
        "backtest_status.request",
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

            # Return lightweight status response (backtest_id only)
            status_response = {
                "run_id": data.get("run_id") or data.get("backtest_id"),
                "status": data.get("status"),
                "strategy_id": data.get("strategy_id"),
                "symbol": data.get("symbol"),
                "created_at": data.get("created_at"),
                "started_at": data.get("started_at"),
                "completed_at": data.get("completed_at"),
                "error_message": data.get("error_message")
            }

            logger.info(
                "backtest_status.success",
                extra={
                    "correlation_id": correlation_id,
                    "run_id": run_id,
                    "status": status_response["status"],
                }
            )

            return status_response

        elif response.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Backtest {run_id} not found")
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Backend error: {response.status_code}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(
            "backtest_status.error",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "error": str(e),
            }
        )

        raise HTTPException(
            status_code=500,
            detail=f"Internal error getting backtest status: {str(e)}"
        )


# --- Backward-compatible aliases using backtests terminology ---

