"""
BFF Proxy Tests

Tests for the HTTP proxy functionality following the acceptance criteria
from Story 8.2 and the QA checklist.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient
import httpx
import json


class TestBacktestsProxy:
    """Test suite for backtests API proxy endpoints."""
    
    def test_proxy_create_backtest_success(self, test_client: TestClient, mock_backend_client):
        """Test successful POST /backtests proxy."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"status": "QUEUED", "run_id": "test-run-123"}
        mock_response.content = json.dumps({"status": "QUEUED", "run_id": "test-run-123"}).encode()
        mock_backend_client.request.return_value = mock_response
        
        request_body = {
            "strategy_id": "sma_crossover",
            "params": {"fast": 10, "slow": 20}
        }
        
        # Act
        response = test_client.post(
            "/api/v1/backtests",
            json=request_body,
            headers={"Idempotency-Key": "test-key-123"}
        )
        
        # Assert
        assert response.status_code == 202
        data = response.json()
        assert data["status"] == "QUEUED"
        assert data["run_id"] == "test-run-123"
        
        # Verify backend was called correctly
        mock_backend_client.request.assert_called_once()
        call_args = mock_backend_client.request.call_args
        assert call_args[1]["method"] == "POST"
        assert call_args[1]["url"] == "/backtests"
        assert "idempotency-key" in call_args[1]["headers"]
    
    def test_proxy_list_backtests_success(self, test_client: TestClient, mock_backend_client):
        """Test successful GET /backtests proxy."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"runs": [], "total": 0}
        mock_response.content = json.dumps({"runs": [], "total": 0}).encode()
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get(
            "/api/v1/backtests",
            params={"limit": 10, "symbol": "AAPL"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "runs" in data
        assert "total" in data
        
        # Verify backend was called with correct parameters
        mock_backend_client.request.assert_called_once()
        call_args = mock_backend_client.request.call_args
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "/backtests"
        assert call_args[1]["params"]["limit"] == 10
        assert call_args[1]["params"]["symbol"] == "AAPL"
    
    def test_proxy_get_backtest_success(self, test_client: TestClient, mock_backend_client):
        """Test successful GET /backtests/{id} proxy."""
        # Arrange
        run_id = "test-run-123"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"run_id": run_id, "status": "COMPLETED"}
        mock_response.content = json.dumps({"run_id": run_id, "status": "COMPLETED"}).encode()
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get(f"/api/v1/backtests/{run_id}")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["run_id"] == run_id
        assert data["status"] == "COMPLETED"
        
        # Verify backend was called correctly
        mock_backend_client.request.assert_called_once()
        call_args = mock_backend_client.request.call_args
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == f"/backtests/{run_id}"
    
    def test_proxy_get_backtest_not_found(self, test_client: TestClient, mock_backend_client):
        """Test GET /backtests/{id} proxy with 404 response."""
        # Arrange
        run_id = "nonexistent-run"
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "error": {"code": "RUN_NOT_FOUND", "message": f"Run {run_id} not found"}
        }
        mock_response.content = json.dumps({
            "error": {"code": "RUN_NOT_FOUND", "message": f"Run {run_id} not found"}
        }).encode()
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get(f"/api/v1/backtests/{run_id}")
        
        # Assert
        assert response.status_code == 404
        data = response.json()
        assert data["error"]["code"] == "RUN_NOT_FOUND"


class TestBarsProxy:
    """Test suite for bars API proxy endpoints."""
    
    def test_proxy_get_daily_bars_success(self, test_client: TestClient, mock_backend_client):
        """Test successful GET /bars/daily proxy."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {
            "symbol": "AAPL",
            "bars": [{"t": "2024-01-01T00:00:00Z", "o": 100.0, "h": 105.0, "l": 99.0, "c": 104.0, "v": 1000}]
        }
        mock_response.content = json.dumps({
            "symbol": "AAPL",
            "bars": [{"t": "2024-01-01T00:00:00Z", "o": 100.0, "h": 105.0, "l": 99.0, "c": 104.0, "v": 1000}]
        }).encode()
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get(
            "/api/v1/bars/daily",
            params={"symbol": "AAPL", "from": "2024-01-01", "to": "2024-01-31"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        assert len(data["bars"]) == 1
        
        # Verify backend was called correctly
        mock_backend_client.request.assert_called_once()
        call_args = mock_backend_client.request.call_args
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "/bars/daily"
        assert call_args[1]["params"]["symbol"] == "AAPL"
        assert call_args[1]["params"]["from"] == "2024-01-01"
        assert call_args[1]["params"]["to"] == "2024-01-31"
    
    def test_proxy_get_minute_bars_success(self, test_client: TestClient, mock_backend_client):
        """Test successful GET /bars/minute proxy."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"symbol": "AAPL", "bars": []}
        mock_response.content = json.dumps({"symbol": "AAPL", "bars": []}).encode()
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get(
            "/api/v1/bars/minute",
            params={"symbol": "AAPL", "from": "2024-01-01", "to": "2024-01-01", "rth_only": True}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"
        
        # Verify backend was called correctly
        mock_backend_client.request.assert_called_once()
        call_args = mock_backend_client.request.call_args
        assert call_args[1]["method"] == "GET"
        assert call_args[1]["url"] == "/bars/minute"
        assert call_args[1]["params"]["rth_only"] is True
    
    def test_proxy_get_hour_bars_success(self, test_client: TestClient, mock_backend_client):
        """Test successful GET /bars/hour proxy."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"symbol": "AAPL", "bars": []}
        mock_response.content = json.dumps({"symbol": "AAPL", "bars": []}).encode()
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get(
            "/api/v1/bars/hour",
            params={"symbol": "AAPL", "from": "2024-01-01", "to": "2024-01-01"}
        )
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["symbol"] == "AAPL"


class TestProxyErrorHandling:
    """Test suite for proxy error handling scenarios."""
    
    def test_proxy_backend_timeout(self, test_client: TestClient, mock_backend_client):
        """Test proxy behavior when backend times out."""
        # Arrange
        mock_backend_client.request.side_effect = httpx.TimeoutException("Request timed out")
        
        # Act
        response = test_client.get("/api/v1/backtests")
        
        # Assert
        assert response.status_code == 504
        data = response.json()
        assert data["error"]["code"] == "BACKEND_TIMEOUT"
        assert "timed out" in data["error"]["message"]
    
    def test_proxy_backend_connection_error(self, test_client: TestClient, mock_backend_client):
        """Test proxy behavior when backend is unavailable."""
        # Arrange
        mock_backend_client.request.side_effect = httpx.ConnectError("Connection failed")
        
        # Act
        response = test_client.get("/api/v1/backtests")
        
        # Assert
        assert response.status_code == 502
        data = response.json()
        assert data["error"]["code"] == "BACKEND_UNAVAILABLE"
        assert "unavailable" in data["error"]["message"]
    
    def test_proxy_general_error(self, test_client: TestClient, mock_backend_client):
        """Test proxy behavior with general errors."""
        # Arrange
        mock_backend_client.request.side_effect = Exception("Unexpected error")
        
        # Act
        response = test_client.get("/api/v1/backtests")
        
        # Assert
        assert response.status_code == 500
        data = response.json()
        assert data["error"]["code"] == "PROXY_ERROR"


class TestAuthenticationPassThrough:
    """Test suite for authentication pass-through functionality."""
    
    def test_authorization_header_forwarded(self, test_client: TestClient, mock_backend_client):
        """Test that Authorization header is forwarded to backend."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"runs": []}
        mock_response.content = json.dumps({"runs": []}).encode()
        mock_backend_client.request.return_value = mock_response
        
        auth_token = "Bearer test-token-123"
        
        # Act
        response = test_client.get(
            "/api/v1/backtests",
            headers={"Authorization": auth_token}
        )
        
        # Assert
        assert response.status_code == 200
        
        # Verify Authorization header was forwarded
        mock_backend_client.request.assert_called_once()
        call_args = mock_backend_client.request.call_args
        assert call_args[1]["headers"]["authorization"] == auth_token
    
    def test_correlation_id_added(self, test_client: TestClient, mock_backend_client):
        """Test that correlation ID is added to backend requests."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.headers = {"content-type": "application/json"}
        mock_response.json.return_value = {"runs": []}
        mock_response.content = json.dumps({"runs": []}).encode()
        mock_backend_client.request.return_value = mock_response
        
        # Act
        response = test_client.get("/api/v1/backtests")
        
        # Assert
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        
        # Verify correlation ID was sent to backend
        mock_backend_client.request.assert_called_once()
        call_args = mock_backend_client.request.call_args
        assert "X-Correlation-ID" in call_args[1]["headers"]
