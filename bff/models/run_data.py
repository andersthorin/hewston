"""
Run Data Models

Pydantic models for run data aggregation requests and responses.
"""

from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime


class RunDetail(BaseModel):
    """Run detail information."""
    
    run_id: str = Field(..., description="Unique run identifier")
    status: str = Field(..., description="Run status (QUEUED, RUNNING, COMPLETED, FAILED)")
    strategy_id: str = Field(..., description="Strategy identifier")
    symbol: str = Field(..., description="Trading symbol")
    created_at: str = Field(..., description="Run creation timestamp")
    started_at: Optional[str] = Field(default=None, description="Run start timestamp")
    completed_at: Optional[str] = Field(default=None, description="Run completion timestamp")
    params: Dict[str, Any] = Field(default_factory=dict, description="Strategy parameters")
    error_message: Optional[str] = Field(default=None, description="Error message if failed")


class RunMetrics(BaseModel):
    """Run performance metrics."""
    
    total_return: Optional[float] = Field(default=None, description="Total return percentage")
    sharpe_ratio: Optional[float] = Field(default=None, description="Sharpe ratio")
    max_drawdown: Optional[float] = Field(default=None, description="Maximum drawdown percentage")
    win_rate: Optional[float] = Field(default=None, description="Win rate percentage")
    profit_factor: Optional[float] = Field(default=None, description="Profit factor")
    total_trades: Optional[int] = Field(default=None, description="Total number of trades")
    winning_trades: Optional[int] = Field(default=None, description="Number of winning trades")
    losing_trades: Optional[int] = Field(default=None, description="Number of losing trades")
    avg_trade_return: Optional[float] = Field(default=None, description="Average trade return")
    avg_winning_trade: Optional[float] = Field(default=None, description="Average winning trade")
    avg_losing_trade: Optional[float] = Field(default=None, description="Average losing trade")
    largest_winner: Optional[float] = Field(default=None, description="Largest winning trade")
    largest_loser: Optional[float] = Field(default=None, description="Largest losing trade")


class EquityPoint(BaseModel):
    """Equity curve data point."""
    
    timestamp: str = Field(..., description="Timestamp")
    equity: float = Field(..., description="Portfolio equity value")
    drawdown: Optional[float] = Field(default=None, description="Drawdown percentage")


class OrderData(BaseModel):
    """Order execution data."""
    
    order_id: str = Field(..., description="Order identifier")
    timestamp: str = Field(..., description="Order timestamp")
    symbol: str = Field(..., description="Trading symbol")
    side: str = Field(..., description="Order side (BUY/SELL)")
    quantity: int = Field(..., description="Order quantity")
    price: float = Field(..., description="Execution price")
    order_type: str = Field(..., description="Order type (MARKET/LIMIT)")
    status: str = Field(..., description="Order status")
    commission: Optional[float] = Field(default=None, description="Commission paid")


class RunDataRequest(BaseModel):
    """Request parameters for run data aggregation."""
    
    include_orders: bool = Field(default=True, description="Include order data")
    include_equity: bool = Field(default=True, description="Include equity curve")
    include_metrics: bool = Field(default=True, description="Include performance metrics")


class RunDataMetadata(BaseModel):
    """Metadata about the aggregated run data response."""
    
    load_time_ms: int = Field(..., description="Response generation time in milliseconds")
    cache_hit: bool = Field(..., description="Whether response came from cache")
    backend_calls: int = Field(..., description="Number of backend API calls made")
    data_sources: List[str] = Field(..., description="Backend endpoints used")
    partial_data: bool = Field(..., description="Whether some data sources failed")
    failed_sources: List[str] = Field(default_factory=list, description="Failed data sources")
    orders_count: Optional[int] = Field(default=None, description="Number of orders included")
    equity_points: Optional[int] = Field(default=None, description="Number of equity points")


class CompleteRunResponse(BaseModel):
    """Complete aggregated run data response."""
    
    run: RunDetail = Field(..., description="Run details")
    metrics: Optional[RunMetrics] = Field(default=None, description="Performance metrics")
    equity: Optional[List[EquityPoint]] = Field(default=None, description="Equity curve data")
    orders: Optional[List[OrderData]] = Field(default=None, description="Order execution data")
    metadata: RunDataMetadata = Field(..., description="Response metadata")


class RunDataError(BaseModel):
    """Error response for run data requests."""
    
    error: Dict[str, Any] = Field(..., description="Error details")
    run_id: Optional[str] = Field(default=None, description="Run ID that caused error")
    partial_data: Optional[CompleteRunResponse] = Field(
        default=None, 
        description="Partial data if some sources succeeded"
    )
