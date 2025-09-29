"""
BFF Health Endpoint Tests

Tests for the health check functionality following the acceptance criteria
from Story 8.1 and the QA checklist.
"""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient


class TestHealthEndpoint:
    """Test suite for BFF health endpoints."""
    
    def test_health_check_success(self, test_client: TestClient, mock_backend_client):
        """Test successful health check with all dependencies healthy."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"status": "ok"}
        mock_backend_client.get.return_value = mock_response
        
        # Act
        response = test_client.get("/api/v1/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "ok"
        assert data["service"] == "hewston-bff"
        assert data["version"] == "0.1.0"
        assert "timestamp" in data
        assert "dependencies" in data
        assert "build_info" in data
        
        # Verify backend dependency check
        assert "backend_api" in data["dependencies"]
        assert data["dependencies"]["backend_api"] == "ok"
    
    def test_health_check_backend_down(self, test_client: TestClient, mock_backend_client):
        """Test health check when backend is down."""
        # Arrange - backend client raises exception
        mock_backend_client.get.side_effect = Exception("Connection failed")
        
        # Act
        response = test_client.get("/api/v1/health")
        
        # Assert
        assert response.status_code == 200  # Health endpoint should still respond
        data = response.json()
        
        assert data["status"] == "degraded"  # Overall status degraded
        assert data["dependencies"]["backend_api"] == "down"
    
    def test_health_check_backend_degraded(self, test_client: TestClient, mock_backend_client):
        """Test health check when backend returns non-200 status."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 500
        mock_backend_client.get.return_value = mock_response
        
        # Act
        response = test_client.get("/api/v1/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "degraded"
        assert data["dependencies"]["backend_api"] == "degraded"
    
    def test_readiness_check_success(self, test_client: TestClient, mock_backend_client):
        """Test readiness check when backend is healthy."""
        # Arrange
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_backend_client.get.return_value = mock_response
        
        # Act
        response = test_client.get("/api/v1/health/ready")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "ready"
    
    def test_readiness_check_backend_down(self, test_client: TestClient, mock_backend_client):
        """Test readiness check when backend is down."""
        # Arrange
        mock_backend_client.get.side_effect = Exception("Connection failed")
        
        # Act
        response = test_client.get("/api/v1/health/ready")
        
        # Assert
        assert response.status_code == 503
        data = response.json()
        assert "Service not ready" in data["detail"]
    
    def test_liveness_check(self, test_client: TestClient):
        """Test liveness check (should always succeed if service is running)."""
        # Act
        response = test_client.get("/api/v1/health/live")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "alive"
    
    def test_health_response_format(self, test_client: TestClient):
        """Test that health response includes all required fields."""
        # Act
        response = test_client.get("/api/v1/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        required_fields = ["status", "service", "version", "timestamp", "dependencies", "build_info"]
        for field in required_fields:
            assert field in data, f"Missing required field: {field}"
        
        # Verify build_info structure
        build_info = data["build_info"]
        assert "service" in build_info
        assert "version" in build_info
        assert "environment" in build_info
        assert "backend_url" in build_info
        assert "feature_flags" in build_info
    
    def test_correlation_id_header(self, test_client: TestClient):
        """Test that correlation ID is added to response headers."""
        # Act
        response = test_client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) == 32  # UUID hex length


class TestHealthIntegration:
    """Integration tests for health check functionality."""

    def test_health_check_with_redis_disabled(self, test_client: TestClient):
        """Test health check when Redis is disabled."""
        # Act
        response = test_client.get("/api/v1/health")

        # Assert
        assert response.status_code == 200
        data = response.json()

        # Redis should not be in dependencies when disabled
        if "redis" in data["dependencies"]:
            assert data["dependencies"]["redis"] == "disabled"

    def test_multiple_health_checks(self, test_client: TestClient):
        """Test multiple consecutive health checks for consistency."""
        # Act - make multiple requests
        responses = [test_client.get("/api/v1/health") for _ in range(3)]

        # Assert - all should succeed
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["service"] == "hewston-bff"
            assert "timestamp" in data
