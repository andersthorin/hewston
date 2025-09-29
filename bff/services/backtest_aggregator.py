from __future__ import annotations

"""
Backtest Data Aggregation Service (canonical)

Handles concurrent backend calls and data aggregation for complete backtest data.
Provides intelligent error handling and partial data recovery.
"""

import asyncio
import logging
import time
from typing import Dict, Any, Optional, List
import json

from bff.models.backtest_data import (
    BacktestDetail,
    BacktestMetrics,
    BacktestEquityPoint,
    BacktestOrderData,
    CompleteBacktestResponse,
    BacktestDataMetadata,
    BacktestDataRequest,
)
from bff.services.backend_client import BackendClient


class BacktestDataAggregator:
    """Service for aggregating backtest data from multiple backend sources."""

    def __init__(self):
        self.logger = logging.getLogger("bff.backtest_aggregator")

    async def aggregate_run_data(
        self,
        run_id: str,
        backend_client: BackendClient,
        request_params: BacktestDataRequest,
        correlation_id: Optional[str] = None,
    ) -> CompleteBacktestResponse:
        """
        Aggregate complete backtest data from multiple backend sources.

        Args:
            run_id: Backtest identifier (retained name for cross-layer compat)
            backend_client: Backend HTTP client
            request_params: Request parameters controlling data inclusion
            correlation_id: Request correlation ID

        Returns:
            CompleteBacktestResponse: Aggregated backtest data
        """
        start_time = time.perf_counter()

        self.logger.info(
            "aggregate.start",
            extra={
                "correlation_id": correlation_id,
                "run_id": run_id,
                "include_orders": request_params.include_orders,
                "include_equity": request_params.include_equity,
                "include_metrics": request_params.include_metrics,
            },
        )

        # Prepare concurrent backend calls
        tasks: List[asyncio.Task] = []
        data_sources: List[str] = []

        # Always fetch backtest details
        tasks.append(self._fetch_run_details(backend_client, run_id, correlation_id))
        data_sources.append("/backtests/{id}")

        # Conditionally fetch other data
        if request_params.include_metrics:
            tasks.append(self._fetch_run_metrics(backend_client, run_id, correlation_id))
            data_sources.append("/backtests/{id}/metrics")
        else:
            tasks.append(asyncio.create_task(self._return_none()))

        if request_params.include_equity:
            tasks.append(self._fetch_equity_curve(backend_client, run_id, correlation_id))
            data_sources.append("/backtests/{id}/equity")
        else:
            tasks.append(asyncio.create_task(self._return_none()))

        if request_params.include_orders:
            tasks.append(self._fetch_order_data(backend_client, run_id, correlation_id))
            data_sources.append("/backtests/{id}/orders")
        else:
            tasks.append(asyncio.create_task(self._return_none()))

        # Execute all requests concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results
            run_details = results[0]
            metrics_data = results[1] if request_params.include_metrics else None
            equity_data = results[2] if request_params.include_equity else None
            orders_data = results[3] if request_params.include_orders else None

            # Handle exceptions and track failures
            failed_sources: List[str] = []
            backend_calls = 1  # Always at least backtest details

            if request_params.include_metrics:
                backend_calls += 1
            if request_params.include_equity:
                backend_calls += 1
            if request_params.include_orders:
                backend_calls += 1

            # Check for details failure (critical)
            if isinstance(run_details, Exception):
                self.logger.error(
                    "aggregate.critical_failure",
                    extra={
                        "correlation_id": correlation_id,
                        "run_id": run_id,
                        "error": str(run_details),
                    },
                )
                raise run_details

            # Optional data failures
            if request_params.include_metrics and isinstance(metrics_data, Exception):
                self.logger.warning(
                    "aggregate.metrics_failure",
                    extra={
                        "correlation_id": correlation_id,
                        "run_id": run_id,
                        "error": str(metrics_data),
                    },
                )
                failed_sources.append("/backtests/{id}/metrics")
                metrics_data = None

            if request_params.include_equity and isinstance(equity_data, Exception):
                self.logger.warning(
                    "aggregate.equity_failure",
                    extra={
                        "correlation_id": correlation_id,
                        "run_id": run_id,
                        "error": str(equity_data),
                    },
                )
                failed_sources.append("/backtests/{id}/equity")
                equity_data = None

            if request_params.include_orders and isinstance(orders_data, Exception):
                self.logger.warning(
                    "aggregate.orders_failure",
                    extra={
                        "correlation_id": correlation_id,
                        "run_id": run_id,
                        "error": str(orders_data),
                    },
                )
                failed_sources.append("/backtests/{id}/orders")
                orders_data = None

            # Transform data
            run_detail = self._transform_run_details(run_details, correlation_id)
            metrics = self._transform_metrics(metrics_data, correlation_id) if metrics_data else None
            equity = self._transform_equity(equity_data, correlation_id) if equity_data else None
            orders = self._transform_orders(orders_data, correlation_id) if orders_data else None

            # Create metadata
            load_time_ms = int((time.perf_counter() - start_time) * 1000)
            metadata = BacktestDataMetadata(
                load_time_ms=load_time_ms,
                cache_hit=False,
                backend_calls=backend_calls,
                data_sources=data_sources,
                partial_data=len(failed_sources) > 0,
                failed_sources=failed_sources,
                orders_count=len(orders) if orders else None,
                equity_points=len(equity) if equity else None,
            )

            response = CompleteBacktestResponse(
                run=run_detail,
                metrics=metrics,
                equity=equity,
                orders=orders,
                metadata=metadata,
            )

            self.logger.info(
                "aggregate.success",
                extra={
                    "correlation_id": correlation_id,
                    "run_id": run_id,
                    "load_time_ms": load_time_ms,
                    "backend_calls": backend_calls,
                    "partial_data": metadata.partial_data,
                    "failed_sources": failed_sources,
                },
            )

            return response

        except Exception as e:
            self.logger.exception(
                "aggregate.error",
                extra={
                    "correlation_id": correlation_id,
                    "run_id": run_id,
                    "error": str(e),
                },
            )
            raise

    async def _fetch_run_details(
        self,
        backend_client: BackendClient,
        run_id: str,
        correlation_id: Optional[str],
    ) -> Dict[str, Any]:
        """Fetch backtest details from backend."""
        response = await backend_client.proxy_request(
            method="GET",
            path=f"/backtests/{run_id}",
            correlation_id=correlation_id,
        )

        if response.status_code == 200:
            response_content = response.body if hasattr(response, "body") else response.content
            response_text = response_content.decode("utf-8") if isinstance(response_content, bytes) else str(response_content)
            return json.loads(response_text)
        elif response.status_code == 404:
            raise ValueError(f"Backtest {run_id} not found")
        else:
            raise RuntimeError(f"Backend error fetching backtest details: {response.status_code}")

    async def _fetch_run_metrics(
        self,
        backend_client: BackendClient,
        run_id: str,
        correlation_id: Optional[str],
    ) -> Dict[str, Any]:
        """Fetch backtest metrics from backend."""
        response = await backend_client.proxy_request(
            method="GET",
            path=f"/backtests/{run_id}/metrics",
            correlation_id=correlation_id,
        )

        if response.status_code == 200:
            response_content = response.body if hasattr(response, "body") else response.content
            response_text = response_content.decode("utf-8") if isinstance(response_content, bytes) else str(response_content)
            return json.loads(response_text)
        elif response.status_code == 404:
            return None
        else:
            raise RuntimeError(f"Backend error fetching metrics: {response.status_code}")

    async def _fetch_equity_curve(
        self,
        backend_client: BackendClient,
        run_id: str,
        correlation_id: Optional[str],
    ) -> Dict[str, Any]:
        """Fetch equity curve from backend."""
        response = await backend_client.proxy_request(
            method="GET",
            path=f"/backtests/{run_id}/equity",
            correlation_id=correlation_id,
        )

        if response.status_code == 200:
            response_content = response.body if hasattr(response, "body") else response.content
            response_text = response_content.decode("utf-8") if isinstance(response_content, bytes) else str(response_content)
            return json.loads(response_text)
        elif response.status_code == 404:
            return None
        else:
            raise RuntimeError(f"Backend error fetching equity: {response.status_code}")

    async def _fetch_order_data(
        self,
        backend_client: BackendClient,
        run_id: str,
        correlation_id: Optional[str],
    ) -> Dict[str, Any]:
        """Fetch order data from backend."""
        response = await backend_client.proxy_request(
            method="GET",
            path=f"/backtests/{run_id}/orders",
            correlation_id=correlation_id,
        )

        if response.status_code == 200:
            response_content = response.body if hasattr(response, "body") else response.content
            response_text = response_content.decode("utf-8") if isinstance(response_content, bytes) else str(response_content)
            return json.loads(response_text)
        elif response.status_code == 404:
            return None
        else:
            raise RuntimeError(f"Backend error fetching orders: {response.status_code}")

    async def _return_none(self) -> None:
        """Helper to return None for disabled data sources."""
        return None

    def _transform_run_details(
        self,
        data: Dict[str, Any],
        correlation_id: Optional[str],
    ) -> BacktestDetail:
        """Transform backend backtest details to frontend format."""
        return BacktestDetail(
            run_id=data.get("run_id", ""),
            status=data.get("status", "UNKNOWN"),
            strategy_id=data.get("strategy_id", ""),
            symbol=data.get("symbol", ""),
            created_at=data.get("created_at", ""),
            started_at=data.get("started_at"),
            completed_at=data.get("completed_at"),
            params=data.get("params", {}),
            error_message=data.get("error_message"),
            dataset_id=data.get("dataset_id"),
            run_from=data.get("run_from"),
            run_to=data.get("run_to"),
        )

    def _transform_metrics(
        self,
        data: Dict[str, Any],
        correlation_id: Optional[str],
    ) -> BacktestMetrics:
        """Transform backend metrics to frontend format."""
        return BacktestMetrics(
            total_return=data.get("total_return"),
            sharpe_ratio=data.get("sharpe_ratio"),
            max_drawdown=data.get("max_drawdown"),
            win_rate=data.get("win_rate"),
            profit_factor=data.get("profit_factor"),
            total_trades=data.get("total_trades"),
            winning_trades=data.get("winning_trades"),
            losing_trades=data.get("losing_trades"),
            avg_trade_return=data.get("avg_trade_return"),
            avg_winning_trade=data.get("avg_winning_trade"),
            avg_losing_trade=data.get("avg_losing_trade"),
            largest_winner=data.get("largest_winner"),
            largest_loser=data.get("largest_loser"),
        )

    def _transform_equity(
        self,
        data: Dict[str, Any],
        correlation_id: Optional[str],
    ) -> List[BacktestEquityPoint]:
        """Transform backend equity data to frontend contract {ts, value, drawdown?}."""
        equity_points: List[BacktestEquityPoint] = []
        for point in (data.get("equity", []) if data else []) or []:
            ts = point.get("ts") or point.get("timestamp") or point.get("ts_utc") or ""
            val = point.get("value") if point.get("value") is not None else point.get("equity")
            if ts in (None, "") or val is None:
                continue
            try:
                import pandas as pd
                ts_iso = pd.to_datetime(ts, utc=True).strftime("%Y-%m-%dT%H:%M:%SZ")
            except Exception:
                ts_iso = str(ts)
            dd = point.get("drawdown")
            try:
                dd_val = float(dd) if dd is not None else None
            except Exception:
                dd_val = None
            try:
                val_f = float(val)
            except Exception:
                continue
            equity_points.append(BacktestEquityPoint(ts=ts_iso, value=val_f, drawdown=dd_val))
        return equity_points

    def _transform_orders(
        self,
        data: Dict[str, Any],
        correlation_id: Optional[str],
    ) -> List[BacktestOrderData]:
        """Transform backend order data to frontend contract with {ts, side, quantity, price, ...}."""
        orders: List[BacktestOrderData] = []
        for order in (data.get("orders", []) if data else []) or []:
            ts = order.get("ts") or order.get("timestamp") or order.get("ts_utc") or ""
            try:
                import pandas as pd
                ts_iso = pd.to_datetime(ts, utc=True).strftime("%Y-%m-%dT%H:%M:%SZ") if ts else ""
            except Exception:
                ts_iso = str(ts) if ts is not None else ""
            # Normalize side to canonical uppercase BUY/SELL expected by frontend tests
            side_out = str(order.get("side") or "").upper()
            qty = order.get("quantity") if order.get("quantity") is not None else order.get("qty")
            try:
                qty_i = int(qty) if qty is not None else 0
            except Exception:
                qty_i = 0
            try:
                price_f = float(order.get("price", 0.0) or 0.0)
            except Exception:
                price_f = 0.0
            orders.append(
                BacktestOrderData(
                    order_id=str(order.get("order_id", "")),
                    ts=ts_iso,
                    symbol=str(order.get("symbol", "")),
                    side=side_out,
                    quantity=qty_i,
                    price=price_f,
                    order_type=str(order.get("order_type") or order.get("type") or ""),
                    status=str(order.get("status") or "FILLED"),
                    commission=(float(order.get("commission")) if order.get("commission") is not None else None),
                )
            )
        return orders


__all__ = ["BacktestDataAggregator"]
