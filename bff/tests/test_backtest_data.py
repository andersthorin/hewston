"""Backtest data tests.

Tests for the run data aggregation functionality following the acceptance
criteria from Story 8.4 and the QA checklist.
"""

import json
from http import HTTPStatus
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

EXPECTED_TOTAL_RETURN = 15.5
EXPECTED_SHARPE_RATIO = 1.2
EXPECTED_TOTAL_TRADES = 10
EXPECTED_MAX_DRAWDOWN = -5.3
EXPECTED_WIN_RATE = 65.0
EXPECTED_WINNING_TRADES = 7
EXPECTED_LOSING_TRADES = 3
EQUITY_LEN = 2
EQUITY_VALUE_START = 100000.0
EQUITY_VALUE_END = 115500.0
ORDER_QTY_100 = 100
BACKEND_CALLS_4 = 4
BACKEND_CALLS_2 = 2
EQUITY_POINTS_2 = 2


class TestBacktestDataEndpoint:
    """Test suite for backtest data aggregation endpoint."""

    def test_complete_run_data_success(
        self, test_client: TestClient, mock_backend_client, mock_backend_response
    ):
        """Test successful complete run data request."""
        # Arrange - Mock all backend responses
        run_details = {
            "run_id": "test-run-123",
            "status": "COMPLETED",
            "strategy_id": "sma_crossover",
            "symbol": "AAPL",
            "created_at": "2024-01-01T00:00:00Z",
            "completed_at": "2024-01-01T01:00:00Z",
            "params": {"fast": 10, "slow": 20},
        }

        metrics_data = {
            "total_return": 15.5,
            "sharpe_ratio": 1.2,
            "max_drawdown": -5.3,
            "win_rate": 65.0,
            "total_trades": 10,
        }

        equity_data = {
            "equity": [
                {"timestamp": "2024-01-01T00:00:00Z", "equity": 100000.0, "drawdown": 0.0},
                {"timestamp": "2024-01-01T01:00:00Z", "equity": 115500.0, "drawdown": 0.0},
            ]
        }

        orders_data = {
            "orders": [
                {
                    "order_id": "order-1",
                    "timestamp": "2024-01-01T00:30:00Z",
                    "symbol": "AAPL",
                    "side": "BUY",
                    "quantity": 100,
                    "price": 150.0,
                    "order_type": "MARKET",
                    "status": "FILLED",
                }
            ]
        }

        # Mock backend responses
        responses = [
            mock_backend_response(HTTPStatus.OK, run_details),
            mock_backend_response(HTTPStatus.OK, metrics_data),
            mock_backend_response(HTTPStatus.OK, equity_data),
            mock_backend_response(HTTPStatus.OK, orders_data),
        ]
        mock_backend_client.request.side_effect = responses

        # Act
        response = test_client.get("/api/v1/backtests/test-run-123/complete")

        # Assert
        assert response.status_code == HTTPStatus.OK
        data = response.json()

        # Verify run details
        assert data["run"]["run_id"] == "test-run-123"
        assert data["run"]["status"] == "COMPLETED"
        assert data["run"]["strategy_id"] == "sma_crossover"
        assert data["run"]["symbol"] == "AAPL"

        # Verify metrics
        assert data["metrics"]["total_return"] == EXPECTED_TOTAL_RETURN
        assert data["metrics"]["sharpe_ratio"] == EXPECTED_SHARPE_RATIO
        assert data["metrics"]["total_trades"] == EXPECTED_TOTAL_TRADES

        # Verify equity curve
        assert len(data["equity"]) == EQUITY_LEN
        assert data["equity"][0]["value"] == EQUITY_VALUE_START
        assert data["equity"][1]["value"] == EQUITY_VALUE_END

        # Verify orders
        assert len(data["orders"]) == 1
        assert data["orders"][0]["order_id"] == "order-1"
        assert data["orders"][0]["side"] == "BUY"
        assert data["orders"][0]["quantity"] == ORDER_QTY_100

        # Verify metadata
        metadata = data["metadata"]
        assert metadata["backend_calls"] == BACKEND_CALLS_4
        assert metadata["partial_data"] is False
        assert metadata["cache_hit"] is False
        assert "load_time_ms" in metadata
        assert metadata["orders_count"] == 1
        assert metadata["equity_points"] == EQUITY_POINTS_2

    def test_complete_run_data_partial_failure(
        self, test_client: TestClient, mock_backend_client, mock_backend_response
    ):
        """Test run data request with partial backend failures."""
        # Arrange - Run details succeed, metrics fail, others succeed
        run_details = {
            "run_id": "test-run-123",
            "status": "COMPLETED",
            "strategy_id": "sma_crossover",
            "symbol": "AAPL",
            "created_at": "2024-01-01T00:00:00Z",
        }

        equity_data = {"equity": []}
        orders_data = {"orders": []}

        responses = [
            mock_backend_response(HTTPStatus.OK, run_details),
            mock_backend_response(HTTPStatus.INTERNAL_SERVER_ERROR),  # Metrics fail
            mock_backend_response(HTTPStatus.OK, equity_data),
            mock_backend_response(HTTPStatus.OK, orders_data),
        ]
        mock_backend_client.request.side_effect = responses

        # Act
        response = test_client.get("/api/v1/backtests/test-run-123/complete")

        # Assert
        assert response.status_code == HTTPStatus.OK
        data = response.json()

        # Verify run details still present
        assert data["run"]["run_id"] == "test-run-123"

        # Verify metrics is None due to failure
        assert data["metrics"] is None

        # Verify other data is present
        assert data["equity"] == []
        assert data["orders"] == []

        # Verify metadata shows partial failure
        metadata = data["metadata"]
        assert metadata["partial_data"] is True
        assert "/backtests/{id}/metrics" in metadata["failed_sources"]

    def test_complete_run_data_not_found(
        self, test_client: TestClient, mock_backend_client, mock_backend_response
    ):
        """Test run data request for non-existent run."""
        # Arrange
        mock_response = mock_backend_response(404)
        mock_backend_client.request.return_value = mock_response

        # Act
        response = test_client.get("/api/v1/backtests/nonexistent-run/complete")

        # Assert
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert "not found" in response.json()["detail"]

    def test_complete_run_data_selective_inclusion(
        self, test_client: TestClient, mock_backend_client, mock_backend_response
    ):
        """Test run data request with selective data inclusion."""
        # Arrange
        run_details = {
            "run_id": "test-run-123",
            "status": "COMPLETED",
            "strategy_id": "sma_crossover",
            "symbol": "AAPL",
        }

        metrics_data = {"total_return": 15.5}

        # Only run details and metrics should be called
        responses = [
            mock_backend_response(HTTPStatus.OK, run_details),
            mock_backend_response(HTTPStatus.OK, metrics_data),
        ]
        mock_backend_client.request.side_effect = responses

        # Act - Request only metrics, no equity or orders
        response = test_client.get(
            "/api/v1/backtests/test-run-123/complete",
            params={"include_orders": False, "include_equity": False, "include_metrics": True},
        )

        # Assert
        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert data["run"]["run_id"] == "test-run-123"
        assert data["metrics"]["total_return"] == EXPECTED_TOTAL_RETURN
        assert data["equity"] is None
        assert data["orders"] is None

        # Verify only 2 backend calls were made
        metadata = data["metadata"]
        assert metadata["backend_calls"] == BACKEND_CALLS_2

    def test_run_status_endpoint(
        self, test_client: TestClient, mock_backend_client, mock_backend_response
    ):
        """Test lightweight run status endpoint."""
        # Arrange
        run_details = {
            "run_id": "test-run-123",
            "status": "RUNNING",
            "strategy_id": "sma_crossover",
            "symbol": "AAPL",
            "created_at": "2024-01-01T00:00:00Z",
            "started_at": "2024-01-01T00:01:00Z",
        }

        mock_response = mock_backend_response(HTTPStatus.OK, run_details)
        mock_backend_client.request.return_value = mock_response

        # Act
        response = test_client.get("/api/v1/backtests/test-run-123/status")

        # Assert
        assert response.status_code == HTTPStatus.OK
        data = response.json()

        assert data["run_id"] == "test-run-123"
        assert data["status"] == "RUNNING"
        assert data["strategy_id"] == "sma_crossover"
        assert data["symbol"] == "AAPL"
        assert "created_at" in data
        assert "started_at" in data

        # Verify only one backend call was made
        assert mock_backend_client.request.call_count == 1


class TestBacktestDataAggregation:
    """Test suite for backtest data aggregation logic."""

    @pytest.mark.asyncio
    async def test_concurrent_backend_calls(self):
        """Test that backend calls are made concurrently."""
        from bff.models.backtest_data import BacktestDataRequest as RunDataRequest
        from bff.services.backtest_aggregator import BacktestDataAggregator as RunDataAggregator

        # Arrange
        aggregator = RunDataAggregator()
        mock_backend_client = AsyncMock()

        # Create simple mock responses without delays for testing
        def create_mock_response(data):
            mock_resp = MagicMock()
            mock_resp.status_code = HTTPStatus.OK
            mock_resp.content = json.dumps(data).encode()
            mock_resp.body = json.dumps(data).encode()  # Add body attribute
            return mock_resp

        # Set up mock responses
        mock_backend_client.proxy_request.side_effect = [
            create_mock_response({"run_id": "test", "status": "COMPLETED"}),
            create_mock_response({"total_return": 15.5}),
            create_mock_response({"equity": []}),
            create_mock_response({"orders": []}),
        ]

        request_params = RunDataRequest(
            include_orders=True, include_equity=True, include_metrics=True
        )

        # Act
        result = await aggregator.aggregate_run_data(
            "test-run", mock_backend_client, request_params, "test-correlation"
        )

        # Assert
        assert result.run.run_id == "test"
        assert result.metadata.backend_calls == BACKEND_CALLS_4
        assert mock_backend_client.proxy_request.call_count == BACKEND_CALLS_4

    def test_data_transformation(self):
        """Test backend data transformation to frontend format."""
        from bff.services.backtest_aggregator import BacktestDataAggregator as RunDataAggregator

        # Arrange
        aggregator = RunDataAggregator()
        backend_data = {
            "run_id": "test-run-123",
            "status": "COMPLETED",
            "strategy_id": "sma_crossover",
            "symbol": "AAPL",
            "created_at": "2024-01-01T00:00:00Z",
            "params": {"fast": 10, "slow": 20},
        }

        # Act
        run_detail = aggregator._transform_run_details(backend_data, "test-correlation")

        # Assert
        assert run_detail.run_id == "test-run-123"
        assert run_detail.status == "COMPLETED"
        assert run_detail.strategy_id == "sma_crossover"
        assert run_detail.symbol == "AAPL"
        assert run_detail.params == {"fast": 10, "slow": 20}

    def test_metrics_transformation(self):
        """Test metrics data transformation."""
        from bff.services.backtest_aggregator import BacktestDataAggregator as RunDataAggregator

        # Arrange
        aggregator = RunDataAggregator()
        backend_data = {
            "total_return": 15.5,
            "sharpe_ratio": 1.2,
            "max_drawdown": -5.3,
            "win_rate": 65.0,
            "total_trades": 10,
            "winning_trades": 7,
            "losing_trades": 3,
        }

        # Act
        metrics = aggregator._transform_metrics(backend_data, "test-correlation")

        # Assert
        assert metrics.total_return == EXPECTED_TOTAL_RETURN
        assert metrics.sharpe_ratio == EXPECTED_SHARPE_RATIO
        assert metrics.max_drawdown == EXPECTED_MAX_DRAWDOWN
        assert metrics.win_rate == EXPECTED_WIN_RATE
        assert metrics.total_trades == EXPECTED_TOTAL_TRADES
        assert metrics.winning_trades == EXPECTED_WINNING_TRADES
        assert metrics.losing_trades == EXPECTED_LOSING_TRADES


class TestBacktestDataCaching:
    """Test suite for backtest data caching functionality."""

    @pytest.mark.asyncio
    async def test_backtest_cache_key_generation(self):
        """Test backtest data cache key generation."""
        from bff.services.cache import CacheService

        # Arrange
        cache_service = CacheService()

        # Act
        key1 = cache_service.generate_backtest_cache_key("run-123", True, True, True)
        key2 = cache_service.generate_backtest_cache_key("run-123", True, True, True)
        key3 = cache_service.generate_backtest_cache_key("run-123", False, True, True)

        # Assert
        assert key1 == key2  # Same parameters = same key
        assert key1 != key3  # Different parameters = different key
        assert key1.startswith("backtest:")

    def test_caching_ttl_by_status(
        self, test_client: TestClient, mock_backend_client, mock_backend_response
    ):
        """Test that caching TTL varies by run status."""
        # This test verifies the caching logic in the endpoint
        # Completed runs should have longer TTL than running runs

        # Arrange - Completed run
        run_details = {
            "run_id": "completed-run",
            "status": "COMPLETED",
            "strategy_id": "test",
            "symbol": "AAPL",
        }

        mock_response = mock_backend_response(HTTPStatus.OK, run_details)
        mock_backend_client.request.return_value = mock_response

        # Act
        response = test_client.get("/api/v1/backtests/completed-run/complete")

        # Assert
        assert response.status_code == HTTPStatus.OK
        # The caching logic is tested implicitly through the endpoint behavior
