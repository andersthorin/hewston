"""
Canonical backtest data models for the BFF layer.

This module defines backtest-centric Pydantic models. Field names intentionally
retain run_id, run_from, run_to for cross-layer compatibility, per project directive.
"""

from __future__ import annotations

from typing import Any
from pydantic import BaseModel, Field


class BacktestDetail(BaseModel):
    """Backtest detail information (frontend contract)."""

    run_id: str = Field(..., description="Unique backtest identifier")
    status: str = Field(..., description="Backtest status (QUEUED, RUNNING, COMPLETED, FAILED)")
    strategy_id: str = Field(..., description="Strategy identifier")
    symbol: str = Field(..., description="Trading symbol")
    created_at: str = Field(..., description="Creation timestamp")
    started_at: str | None = Field(default=None, description="Start timestamp")
    completed_at: str | None = Field(default=None, description="Completion timestamp")
    params: dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    error_message: str | None = Field(default=None, description="Error message if failed")
    # BFF additions propagated from backend manifest/details when available
    dataset_id: str | None = Field(default=None, description="Dataset identifier for this backtest")
    run_from: str | None = Field(
        default=None, description="Backtest window start date (YYYY-MM-DD)"
    )
    run_to: str | None = Field(default=None, description="Backtest window end date (YYYY-MM-DD)")


class BacktestMetrics(BaseModel):
    """Backtest performance metrics."""

    total_return: float | None = Field(default=None, description="Total return percentage")
    sharpe_ratio: float | None = Field(default=None, description="Sharpe ratio")
    max_drawdown: float | None = Field(default=None, description="Maximum drawdown percentage")
    win_rate: float | None = Field(default=None, description="Win rate percentage")
    profit_factor: float | None = Field(default=None, description="Profit factor")
    total_trades: int | None = Field(default=None, description="Total number of trades")
    winning_trades: int | None = Field(default=None, description="Number of winning trades")
    losing_trades: int | None = Field(default=None, description="Number of losing trades")
    avg_trade_return: float | None = Field(default=None, description="Average trade return")
    avg_winning_trade: float | None = Field(default=None, description="Average winning trade")
    avg_losing_trade: float | None = Field(default=None, description="Average losing trade")
    largest_winner: float | None = Field(default=None, description="Largest winning trade")
    largest_loser: float | None = Field(default=None, description="Largest losing trade")


class BacktestEquityPoint(BaseModel):
    """Equity curve data point (frontend contract)."""

    ts: str = Field(..., description="Timestamp (ISO string)")
    value: float = Field(..., description="Portfolio equity value")
    drawdown: float | None = Field(default=None, description="Drawdown percentage")


class BacktestOrderData(BaseModel):
    """Order execution data (frontend contract)."""

    order_id: str = Field(..., description="Order identifier")
    ts: str = Field(..., description="Order timestamp (ISO string)")
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="Order side (buy/sell)")
    quantity: int = Field(..., description="Order quantity")
    price: float = Field(..., description="Execution price")
    order_type: str = Field(..., description="Order type (MARKET/LIMIT)")
    status: str = Field(..., description="Order status")
    commission: float | None = Field(default=None, description="Commission paid")


class BacktestDataRequest(BaseModel):
    """Request parameters for backtest data aggregation."""

    include_orders: bool = Field(default=True, description="Include order data")
    include_equity: bool = Field(default=True, description="Include equity curve")
    include_metrics: bool = Field(default=True, description="Include performance metrics")


class BacktestDataMetadata(BaseModel):
    """Metadata about the aggregated backtest data response."""

    load_time_ms: int = Field(..., description="Response generation time in milliseconds")
    cache_hit: bool = Field(..., description="Whether response came from cache")
    backend_calls: int = Field(..., description="Number of backend API calls made")
    data_sources: list[str] = Field(..., description="Backend endpoints used")
    partial_data: bool = Field(..., description="Whether some data sources failed")
    failed_sources: list[str] = Field(default_factory=list, description="Failed data sources")
    orders_count: int | None = Field(default=None, description="Number of orders included")
    equity_points: int | None = Field(default=None, description="Number of equity points")


class CompleteBacktestResponse(BaseModel):
    """Complete aggregated backtest data response."""

    run: BacktestDetail = Field(..., description="Backtest details")
    metrics: BacktestMetrics | None = Field(default=None, description="Performance metrics")
    equity: list[BacktestEquityPoint] | None = Field(default=None, description="Equity curve data")
    orders: list[BacktestOrderData] | None = Field(default=None, description="Order execution data")
    metadata: BacktestDataMetadata = Field(..., description="Response metadata")


class BacktestDataError(BaseModel):
    """Error response for backtest data requests."""

    error: dict[str, Any] = Field(..., description="Error details")
    run_id: str | None = Field(default=None, description="Backtest ID that caused error")
    partial_data: CompleteBacktestResponse | None = Field(
        default=None,
        description="Partial data if some sources succeeded",
    )
