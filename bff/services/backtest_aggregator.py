from __future__ import annotations

"""
Backtest Data Aggregation Service (canonical)

Handles concurrent backend calls and data aggregation for complete backtest data.
Provides intelligent error handling and partial data recovery.
"""

import asyncio
import json
import logging
import time
from typing import Any

from bff.models.backtest_data import (
    BacktestDataMetadata,
    BacktestDataRequest,
    BacktestDetail,
    BacktestEquityPoint,
    BacktestMetrics,
    BacktestOrderData,
    CompleteBacktestResponse,
)
from bff.services.backend_client import BackendClient


class BacktestDataAggregator:
    """Service for aggregating backtest data from multiple backend sources."""

    def __init__(self):
        self.logger = logging.getLogger("bff.backtest_aggregator")


    async def _build_fetch_tasks(
        self,
        backend_client: BackendClient,
        run_id: str,
        request_params: BacktestDataRequest,
        correlation_id: str | None,
    ) -> tuple[list[asyncio.Task], list[str]]:
        tasks: list[asyncio.Task] = []
        data_sources: list[str] = []
        tasks.append(self._fetch_run_details(backend_client, run_id, correlation_id))
        data_sources.append("/backtests/{id}")
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
        return tasks, data_sources

    def _normalize_results(
        self,
        results: list[Any],
        request_params: BacktestDataRequest,
        correlation_id: str | None,
    ) -> tuple[dict | Exception, dict | None, dict | None, dict | None, list[str], int]:
        run_details = results[0]
        metrics_data = results[1] if request_params.include_metrics else None
        equity_data = results[2] if request_params.include_equity else None
        orders_data = results[3] if request_params.include_orders else None
        failed_sources: list[str] = []
        backend_calls = 1
        if request_params.include_metrics:
            backend_calls += 1
        if request_params.include_equity:
            backend_calls += 1
        if request_params.include_orders:
            backend_calls += 1
        if request_params.include_metrics and isinstance(metrics_data, Exception):
            self.logger.warning(
                "aggregate.metrics_failure",
                extra={"correlation_id": correlation_id, "run_id": None, "error": str(metrics_data)},
            )
            failed_sources.append("/backtests/{id}/metrics")
            metrics_data = None
        if request_params.include_equity and isinstance(equity_data, Exception):
            self.logger.warning(
                "aggregate.equity_failure",
                extra={"correlation_id": correlation_id, "run_id": None, "error": str(equity_data)},
            )
            failed_sources.append("/backtests/{id}/equity")
            equity_data = None
        if request_params.include_orders and isinstance(orders_data, Exception):
            self.logger.warning(
                "aggregate.orders_failure",
                extra={"correlation_id": correlation_id, "run_id": None, "error": str(orders_data)},
            )
            failed_sources.append("/backtests/{id}/orders")
            orders_data = None
        return run_details, metrics_data, equity_data, orders_data, failed_sources, backend_calls

    async def aggregate_run_data(
        self,
        run_id: str,
        backend_client: BackendClient,
        request_params: BacktestDataRequest,
        correlation_id: str | None = None,
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
        tasks, data_sources = await self._build_fetch_tasks(backend_client, run_id, request_params, correlation_id)

        # Execute all requests concurrently
        try:
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Process results and normalize
            run_details, metrics_data, equity_data, orders_data, failed_sources, backend_calls = self._normalize_results(
                results, request_params, correlation_id
            )

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

            # Transform data
            run_detail = self._transform_run_details(run_details, correlation_id)
            metrics = (
                self._transform_metrics(metrics_data, correlation_id) if metrics_data else None
            )
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
        correlation_id: str | None,
    ) -> dict[str, Any]:
        """Fetch backtest details from backend."""
        response = await backend_client.proxy_request(
            method="GET",
            path=f"/backtests/{run_id}",
            correlation_id=correlation_id,
        )

        if response.status_code == 200:
            response_content = response.body if hasattr(response, "body") else response.content
            response_text = (
                response_content.decode("utf-8")
                if isinstance(response_content, bytes)
                else str(response_content)
            )
            return json.loads(response_text)
        elif response.status_code == 404:
            raise ValueError(f"Backtest {run_id} not found")
        else:
            raise RuntimeError(f"Backend error fetching backtest details: {response.status_code}")

    async def _fetch_run_metrics(
        self,
        backend_client: BackendClient,
        run_id: str,
        correlation_id: str | None,
    ) -> dict[str, Any]:
        """Fetch backtest metrics from backend."""
        response = await backend_client.proxy_request(
            method="GET",
            path=f"/backtests/{run_id}/metrics",
            correlation_id=correlation_id,
        )

        if response.status_code == 200:
            response_content = response.body if hasattr(response, "body") else response.content
            response_text = (
                response_content.decode("utf-8")
                if isinstance(response_content, bytes)
                else str(response_content)
            )
            return json.loads(response_text)
        elif response.status_code == 404:
            return None
        else:
            raise RuntimeError(f"Backend error fetching metrics: {response.status_code}")

    async def _fetch_equity_curve(
        self,
        backend_client: BackendClient,
        run_id: str,
        correlation_id: str | None,
    ) -> dict[str, Any]:
        """Fetch equity curve from backend."""
        response = await backend_client.proxy_request(
            method="GET",
            path=f"/backtests/{run_id}/equity",
            correlation_id=correlation_id,
        )

        if response.status_code == 200:
            response_content = response.body if hasattr(response, "body") else response.content
            response_text = (
                response_content.decode("utf-8")
                if isinstance(response_content, bytes)
                else str(response_content)
            )
            return json.loads(response_text)
        elif response.status_code == 404:
            return None
        else:
            raise RuntimeError(f"Backend error fetching equity: {response.status_code}")

    async def _fetch_order_data(
        self,
        backend_client: BackendClient,
        run_id: str,
        correlation_id: str | None,
    ) -> dict[str, Any]:
        """Fetch order data from backend."""
        response = await backend_client.proxy_request(
            method="GET",
            path=f"/backtests/{run_id}/orders",
            correlation_id=correlation_id,
        )

        if response.status_code == 200:
            response_content = response.body if hasattr(response, "body") else response.content
            response_text = (
                response_content.decode("utf-8")
                if isinstance(response_content, bytes)
                else str(response_content)
            )
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
        data: dict[str, Any],
        correlation_id: str | None,
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
        data: dict[str, Any],
        correlation_id: str | None,
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
        data: dict[str, Any],
        correlation_id: str | None,
    ) -> list[BacktestEquityPoint]:
        """Transform backend equity data to frontend contract {ts, value, drawdown?}.
        Avoid per-row pandas conversions; backend already emits ISO timestamps.
        """
        out: list[BacktestEquityPoint] = []
        items = (data.get("equity", []) if data else []) or []
        for point in items:
            ts = point.get("timestamp") or point.get("ts") or point.get("ts_utc") or ""
            if not ts:
                continue
            # Trust backend ISO strings; otherwise fallback to simple str()
            ts_iso = ts if isinstance(ts, str) else str(ts)
            val = point.get("equity") if point.get("equity") is not None else point.get("value")
            if val is None:
                continue
            try:
                val_f = float(val)
            except Exception:
                continue
            dd = point.get("drawdown")
            try:
                dd_val = float(dd) if dd is not None else None
            except Exception:
                dd_val = None
            out.append(BacktestEquityPoint(ts=ts_iso, value=val_f, drawdown=dd_val))
        return out

    def _transform_orders(
        self,
        data: dict[str, Any],
        correlation_id: str | None,
    ) -> list[BacktestOrderData]:
        """Transform backend order data to frontend contract with {ts, side, quantity, price, ...}.
        Avoid per-row pandas conversions; backend already emits ISO timestamps.
        """
        out: list[BacktestOrderData] = []
        items = (data.get("orders", []) if data else []) or []
        for order in items:
            ts = order.get("timestamp") or order.get("ts") or order.get("ts_utc") or ""
            ts_iso = ts if isinstance(ts, str) else (str(ts) if ts is not None else "")
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
            out.append(
                BacktestOrderData(
                    order_id=str(order.get("order_id", "")),
                    ts=ts_iso,
                    symbol=str(order.get("symbol", "")),
                    side=side_out,
                    quantity=qty_i,
                    price=price_f,
                    order_type=str(order.get("order_type") or order.get("type") or ""),
                    status=str(order.get("status") or "FILLED"),
                    commission=(
                        float(order.get("commission"))
                        if order.get("commission") is not None
                        else None
                    ),
                )
            )
        return out


__all__ = ["BacktestDataAggregator"]
