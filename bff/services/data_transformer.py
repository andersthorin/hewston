"""
Data Transformation Service

Handles data transformation, aggregation, and decimation for chart data.
Moves complex data processing logic from frontend to BFF layer.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import math

from bff.models.chart_data import BarData, TimeframeEnum


class DataTransformer:
    """Service for transforming and optimizing chart data."""
    
    def __init__(self):
        self.logger = logging.getLogger("bff.data_transformer")
    
    def transform_backend_bars(
        self,
        backend_data: Dict[str, Any],
        timeframe: TimeframeEnum,
        correlation_id: Optional[str] = None
    ) -> List[BarData]:
        """
        Transform backend bar data to frontend-optimized format.
        
        Args:
            backend_data: Raw data from backend API
            timeframe: Requested timeframe
            correlation_id: Request correlation ID
            
        Returns:
            List[BarData]: Transformed bar data
        """
        self.logger.info(
            "transform.start",
            extra={
                "correlation_id": correlation_id,
                "timeframe": timeframe,
                "backend_bars_count": len(backend_data.get("bars", [])),
            }
        )
        
        bars = []
        backend_bars = backend_data.get("bars", [])
        
        for bar in backend_bars:
            try:
                # Transform backend bar format to frontend format
                transformed_bar = BarData(
                    timestamp=self._normalize_timestamp(bar.get("t")),
                    open=float(bar.get("o", 0)),
                    high=float(bar.get("h", 0)),
                    low=float(bar.get("l", 0)),
                    close=float(bar.get("c", 0)),
                    volume=int(bar.get("v", 0)) if bar.get("v") is not None else 0
                )
                bars.append(transformed_bar)
                
            except (ValueError, TypeError) as e:
                self.logger.warning(
                    "transform.bar_error",
                    extra={
                        "correlation_id": correlation_id,
                        "bar_data": bar,
                        "error": str(e),
                    }
                )
                continue
        
        self.logger.info(
            "transform.complete",
            extra={
                "correlation_id": correlation_id,
                "input_bars": len(backend_bars),
                "output_bars": len(bars),
                "timeframe": timeframe,
            }
        )
        
        return bars
    
    def decimate_data(
        self,
        bars: List[BarData],
        target_points: int,
        correlation_id: Optional[str] = None
    ) -> Tuple[List[BarData], int]:
        """
        Decimate bar data to target number of points.
        
        Uses intelligent sampling to preserve important price movements
        while reducing data size for performance.
        
        Args:
            bars: Original bar data
            target_points: Target number of data points
            correlation_id: Request correlation ID
            
        Returns:
            Tuple[List[BarData], int]: (decimated_bars, stride_used)
        """
        if len(bars) <= target_points:
            self.logger.info(
                "decimate.skip",
                extra={
                    "correlation_id": correlation_id,
                    "bars_count": len(bars),
                    "target_points": target_points,
                    "reason": "data_already_small",
                }
            )
            return bars, 1
        
        # Calculate stride for uniform sampling
        stride = max(1, len(bars) // target_points)
        
        self.logger.info(
            "decimate.start",
            extra={
                "correlation_id": correlation_id,
                "input_bars": len(bars),
                "target_points": target_points,
                "calculated_stride": stride,
            }
        )
        
        # Use uniform sampling with stride
        decimated_bars = []
        for i in range(0, len(bars), stride):
            decimated_bars.append(bars[i])

        # Always include the last bar if it wasn't included and we're not over target
        if (len(bars) > 0 and
            (len(bars) - 1) % stride != 0 and
            len(decimated_bars) < target_points):
            decimated_bars.append(bars[-1])
        
        self.logger.info(
            "decimate.complete",
            extra={
                "correlation_id": correlation_id,
                "input_bars": len(bars),
                "output_bars": len(decimated_bars),
                "stride_used": stride,
                "reduction_ratio": len(decimated_bars) / len(bars) if bars else 0,
            }
        )
        
        return decimated_bars, stride
    
    def aggregate_timeframe_data(
        self,
        daily_data: Optional[Dict[str, Any]] = None,
        hourly_data: Optional[Dict[str, Any]] = None,
        minute_data: Optional[Dict[str, Any]] = None,
        timeframe: TimeframeEnum = TimeframeEnum.DAILY,
        correlation_id: Optional[str] = None
    ) -> List[BarData]:
        """
        Aggregate data from multiple timeframes if needed.
        
        For future use when combining multiple data sources.
        Currently uses single timeframe data.
        
        Args:
            daily_data: Daily bar data from backend
            hourly_data: Hourly bar data from backend
            minute_data: Minute bar data from backend
            timeframe: Requested timeframe
            correlation_id: Request correlation ID
            
        Returns:
            List[BarData]: Aggregated bar data
        """
        # For now, use single timeframe data
        # Future enhancement: intelligent data combination
        
        if timeframe == TimeframeEnum.DAILY and daily_data:
            return self.transform_backend_bars(daily_data, timeframe, correlation_id)
        elif timeframe == TimeframeEnum.HOURLY and hourly_data:
            return self.transform_backend_bars(hourly_data, timeframe, correlation_id)
        elif timeframe in [TimeframeEnum.MINUTE, TimeframeEnum.MINUTE_DECIMATED] and minute_data:
            return self.transform_backend_bars(minute_data, timeframe, correlation_id)
        else:
            self.logger.warning(
                "aggregate.no_data",
                extra={
                    "correlation_id": correlation_id,
                    "timeframe": timeframe,
                    "has_daily": daily_data is not None,
                    "has_hourly": hourly_data is not None,
                    "has_minute": minute_data is not None,
                }
            )
            return []
    
    def _normalize_timestamp(self, timestamp: Any) -> str:
        """
        Normalize timestamp to ISO format.
        
        Args:
            timestamp: Timestamp in various formats
            
        Returns:
            str: ISO formatted timestamp
        """
        if isinstance(timestamp, str):
            # Already a string, assume it's properly formatted
            return timestamp
        elif isinstance(timestamp, datetime):
            return timestamp.isoformat()
        elif isinstance(timestamp, (int, float)):
            # Unix timestamp
            return datetime.fromtimestamp(timestamp).isoformat()
        else:
            # Fallback to string representation
            return str(timestamp)
    
    def validate_bar_data(
        self,
        bars: List[BarData],
        correlation_id: Optional[str] = None
    ) -> List[BarData]:
        """
        Validate and clean bar data.
        
        Args:
            bars: Bar data to validate
            correlation_id: Request correlation ID
            
        Returns:
            List[BarData]: Validated bar data
        """
        valid_bars = []
        invalid_count = 0
        
        for bar in bars:
            # Basic validation: prices should be positive
            if (bar.open > 0 and bar.high > 0 and bar.low > 0 and bar.close > 0 and
                bar.high >= bar.low and bar.high >= bar.open and bar.high >= bar.close and
                bar.low <= bar.open and bar.low <= bar.close):
                valid_bars.append(bar)
            else:
                invalid_count += 1
        
        if invalid_count > 0:
            self.logger.warning(
                "validate.invalid_bars",
                extra={
                    "correlation_id": correlation_id,
                    "total_bars": len(bars),
                    "invalid_bars": invalid_count,
                    "valid_bars": len(valid_bars),
                }
            )
        
        return valid_bars
