"""
Chart Data Tests

Tests for the chart data aggregation functionality following the acceptance criteria
from Story 8.3 and the QA checklist.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
import json
from datetime import date


class TestChartDataEndpoint:
    """Test suite for chart data aggregation endpoint."""
    
    def test_chart_data_daily_success(self, test_client: TestClient, mock_backend_client, mock_backend_response):
        """Test successful daily chart data request."""
        # Arrange
        backend_data = {
            "symbol": "AAPL",
            "bars": [
                {"t": "2024-01-01T00:00:00Z", "o": 100.0, "h": 105.0, "l": 99.0, "c": 104.0, "v": 1000},
                {"t": "2024-01-02T00:00:00Z", "o": 104.0, "h": 108.0, "l": 103.0, "c": 107.0, "v": 1200}
            ]
        }
        mock_response = mock_backend_response(200, backend_data)
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get(
            "/api/v1/chart-data",
            params={
                "symbol": "AAPL",
                "timeframe": "1D",
                "from": "2024-01-01",
                "to": "2024-01-31",
                "target_points": 10000
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == "AAPL"
        assert data["timeframe"] == "1D"
        assert data["from_date"] == "2024-01-01"
        assert data["to_date"] == "2024-01-31"
        assert len(data["bars"]) == 2
        
        # Verify metadata
        metadata = data["metadata"]
        assert metadata["total_bars"] == 2
        assert metadata["decimated"] is False
        assert metadata["cache_hit"] is False
        assert metadata["backend_calls"] == 1
        assert metadata["data_source"] == "/bars/daily"
        assert "load_time_ms" in metadata
    
    def test_chart_data_minute_decimated(self, test_client: TestClient, mock_backend_client, mock_backend_response):
        """Test minute chart data with decimation."""
        # Arrange - large dataset that will be decimated
        bars = []
        for i in range(20000):  # More than target_points
            bars.append({
                "t": f"2024-01-01T{i//3600:02d}:{(i%3600)//60:02d}:{i%60:02d}Z",
                "o": 100.0 + i * 0.01,
                "h": 101.0 + i * 0.01,
                "l": 99.0 + i * 0.01,
                "c": 100.5 + i * 0.01,
                "v": 100
            })

        backend_data = {
            "symbol": "AAPL",
            "bars": bars
        }
        mock_response = mock_backend_response(200, backend_data)
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get(
            "/api/v1/chart-data",
            params={
                "symbol": "AAPL",
                "timeframe": "1M",
                "from": "2024-01-01",
                "to": "2024-01-01",
                "target_points": 5000
            }
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["symbol"] == "AAPL"
        assert data["timeframe"] == "1M"
        assert len(data["bars"]) <= 5000  # Should be decimated
        
        # Verify decimation metadata
        metadata = data["metadata"]
        assert metadata["decimated"] is True
        assert metadata["decimation_stride"] is not None
        assert metadata["decimation_stride"] > 1
    
    def test_chart_data_validation_error(self, test_client: TestClient):
        """Test chart data request with validation errors."""
        # Act - invalid date range
        response = test_client.get(
            "/api/v1/chart-data",
            params={
                "symbol": "AAPL",
                "timeframe": "1D",
                "from": "2024-01-31",  # After to_date
                "to": "2024-01-01",
                "target_points": 10000
            }
        )
        
        # Assert
        assert response.status_code == 400
        assert "to_date must be after from_date" in response.json()["detail"]
    
    def test_chart_data_symbol_not_found(self, test_client: TestClient, mock_backend_client, mock_backend_response):
        """Test chart data request for non-existent symbol."""
        # Arrange
        mock_response = mock_backend_response(404)
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get(
            "/api/v1/chart-data",
            params={
                "symbol": "NONEXISTENT",
                "timeframe": "1D",
                "from": "2024-01-01",
                "to": "2024-01-31"
            }
        )
        
        # Assert
        assert response.status_code == 404
        assert "No data found" in response.json()["detail"]
    
    def test_chart_data_backend_error(self, test_client: TestClient, mock_backend_client, mock_backend_response):
        """Test chart data request with backend error."""
        # Arrange
        mock_response = mock_backend_response(500)
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get(
            "/api/v1/chart-data",
            params={
                "symbol": "AAPL",
                "timeframe": "1D",
                "from": "2024-01-01",
                "to": "2024-01-31"
            }
        )
        
        # Assert
        assert response.status_code == 500
        assert "Backend error" in response.json()["detail"]


class TestDataTransformation:
    """Test suite for data transformation functionality."""
    
    def test_transform_backend_bars(self):
        """Test backend bar data transformation."""
        from bff.services.data_transformer import DataTransformer
        from bff.models.chart_data import TimeframeEnum
        
        # Arrange
        transformer = DataTransformer()
        backend_data = {
            "symbol": "AAPL",
            "bars": [
                {"t": "2024-01-01T00:00:00Z", "o": 100.0, "h": 105.0, "l": 99.0, "c": 104.0, "v": 1000},
                {"t": "2024-01-02T00:00:00Z", "o": 104.0, "h": 108.0, "l": 103.0, "c": 107.0, "v": 1200}
            ]
        }
        
        # Act
        bars = transformer.transform_backend_bars(
            backend_data,
            TimeframeEnum.DAILY,
            "test-correlation-id"
        )
        
        # Assert
        assert len(bars) == 2
        assert bars[0].timestamp == "2024-01-01T00:00:00Z"
        assert bars[0].open == 100.0
        assert bars[0].high == 105.0
        assert bars[0].low == 99.0
        assert bars[0].close == 104.0
        assert bars[0].volume == 1000
    
    def test_decimate_data(self):
        """Test data decimation functionality."""
        from bff.services.data_transformer import DataTransformer
        from bff.models.chart_data import BarData
        
        # Arrange
        transformer = DataTransformer()
        bars = []
        for i in range(1000):
            bars.append(BarData(
                timestamp=f"2024-01-01T{i//60:02d}:{i%60:02d}:00Z",
                open=100.0 + i * 0.01,
                high=101.0 + i * 0.01,
                low=99.0 + i * 0.01,
                close=100.5 + i * 0.01,
                volume=100
            ))
        
        # Act
        decimated_bars, stride = transformer.decimate_data(
            bars,
            target_points=100,
            correlation_id="test-correlation-id"
        )
        
        # Assert
        assert len(decimated_bars) <= 100
        assert stride > 1
        assert decimated_bars[0] == bars[0]  # First bar preserved
        # Last bar may or may not be preserved depending on stride and target_points
        assert len(decimated_bars) < len(bars)  # Data was actually decimated
    
    def test_validate_bar_data(self):
        """Test bar data validation."""
        from bff.services.data_transformer import DataTransformer
        from bff.models.chart_data import BarData
        
        # Arrange
        transformer = DataTransformer()
        bars = [
            # Valid bar
            BarData(
                timestamp="2024-01-01T00:00:00Z",
                open=100.0, high=105.0, low=99.0, close=104.0, volume=1000
            ),
            # Invalid bar (negative prices)
            BarData(
                timestamp="2024-01-01T01:00:00Z",
                open=-100.0, high=105.0, low=99.0, close=104.0, volume=1000
            ),
            # Invalid bar (high < low)
            BarData(
                timestamp="2024-01-01T02:00:00Z",
                open=100.0, high=95.0, low=99.0, close=104.0, volume=1000
            )
        ]
        
        # Act
        valid_bars = transformer.validate_bar_data(bars, "test-correlation-id")
        
        # Assert
        assert len(valid_bars) == 1  # Only first bar is valid
        assert valid_bars[0].open == 100.0


class TestCaching:
    """Test suite for caching functionality."""
    
    @pytest.mark.asyncio
    async def test_cache_key_generation(self):
        """Test cache key generation."""
        from bff.services.cache import CacheService
        
        # Arrange
        cache_service = CacheService()
        
        # Act
        key1 = cache_service.generate_chart_cache_key(
            "AAPL", "1D", "2024-01-01", "2024-01-31", 10000, True
        )
        key2 = cache_service.generate_chart_cache_key(
            "AAPL", "1D", "2024-01-01", "2024-01-31", 10000, True
        )
        key3 = cache_service.generate_chart_cache_key(
            "AAPL", "1H", "2024-01-01", "2024-01-31", 10000, True
        )
        
        # Assert
        assert key1 == key2  # Same parameters = same key
        assert key1 != key3  # Different timeframe = different key
        assert key1.startswith("chart:")
    
    @pytest.mark.asyncio
    async def test_cache_disabled(self):
        """Test cache behavior when disabled."""
        from bff.services.cache import CacheService
        
        # Arrange
        cache_service = CacheService(redis_client=None)  # No Redis client
        
        # Act
        result = await cache_service.get_chart_data("test-key", "test-correlation-id")
        
        # Assert
        assert result is None
        assert not cache_service.enabled
    
    def test_calculate_ttl(self):
        """Test TTL calculation based on data recency."""
        from bff.services.cache import CacheService
        from datetime import datetime, timedelta
        
        # Arrange
        cache_service = CacheService()
        now = datetime.now()
        
        # Act & Assert
        # Recent data (today)
        recent_date = now.isoformat()
        ttl_recent = cache_service.calculate_ttl("2024-01-01", recent_date, "1D")
        assert ttl_recent == 300  # 5 minutes
        
        # Week old data
        week_old = (now - timedelta(days=7)).isoformat()
        ttl_week = cache_service.calculate_ttl("2024-01-01", week_old, "1D")
        assert ttl_week == 3600  # 1 hour
        
        # Historical data
        historical = (now - timedelta(days=100)).isoformat()
        ttl_historical = cache_service.calculate_ttl("2024-01-01", historical, "1D")
        assert ttl_historical == 86400  # 24 hours
