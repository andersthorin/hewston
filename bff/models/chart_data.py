"""
Chart Data Models

Pydantic models for chart data aggregation requests and responses.
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict, Any
from datetime import date, datetime
from enum import Enum


class TimeframeEnum(str, Enum):
    """Supported timeframes for chart data."""
    DAILY = "1D"
    HOURLY = "1H"
    MINUTE = "1M"
    MINUTE_DECIMATED = "1M_DECIMATED"


class ChartDataRequest(BaseModel):
    """Request model for unified chart data endpoint."""
    
    symbol: str = Field(..., description="Trading symbol (e.g., 'AAPL')")
    timeframe: TimeframeEnum = Field(..., description="Data timeframe")
    from_date: date = Field(..., description="Start date for data range")
    to_date: date = Field(..., description="End date for data range")
    target_points: Optional[int] = Field(
        default=10000,
        ge=100,
        le=50000,
        description="Target number of data points for decimation"
    )
    rth_only: bool = Field(
        default=True,
        description="Regular trading hours only (for intraday data)"
    )
    
    @field_validator('to_date')
    @classmethod
    def validate_date_range(cls, v, info):
        """Validate that to_date is after from_date."""
        if info.data and 'from_date' in info.data and v < info.data['from_date']:
            raise ValueError('to_date must be after from_date')
        return v

    @field_validator('symbol')
    @classmethod
    def validate_symbol(cls, v):
        """Validate symbol format."""
        if not v or not v.strip():
            raise ValueError('symbol cannot be empty')
        return v.upper().strip()


class BarData(BaseModel):
    """Individual bar data point."""
    
    timestamp: str = Field(..., description="ISO timestamp")
    open: float = Field(..., description="Opening price")
    high: float = Field(..., description="High price")
    low: float = Field(..., description="Low price")
    close: float = Field(..., description="Closing price")
    volume: Optional[int] = Field(default=0, description="Volume")


class ResponseMetadata(BaseModel):
    """Metadata about the response."""
    
    total_bars: int = Field(..., description="Total number of bars returned")
    decimated: bool = Field(..., description="Whether data was decimated")
    decimation_stride: Optional[int] = Field(
        default=None,
        description="Decimation stride used (if decimated)"
    )
    cache_hit: bool = Field(..., description="Whether response came from cache")
    load_time_ms: int = Field(..., description="Response generation time in milliseconds")
    backend_calls: int = Field(..., description="Number of backend API calls made")
    data_source: str = Field(..., description="Source of the data (backend endpoint)")


class ChartDataResponse(BaseModel):
    """Response model for unified chart data endpoint."""
    
    symbol: str = Field(..., description="Trading symbol")
    timeframe: str = Field(..., description="Data timeframe")
    from_date: str = Field(..., description="Start date (ISO format)")
    to_date: str = Field(..., description="End date (ISO format)")
    bars: List[BarData] = Field(..., description="OHLCV bar data")
    metadata: ResponseMetadata = Field(..., description="Response metadata")


class ChartDataError(BaseModel):
    """Error response for chart data requests."""
    
    error: Dict[str, Any] = Field(..., description="Error details")
    symbol: Optional[str] = Field(default=None, description="Symbol that caused error")
    timeframe: Optional[str] = Field(default=None, description="Timeframe that caused error")
