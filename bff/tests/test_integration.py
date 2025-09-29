"""
BFF Integration Tests

Integration tests that verify BFF service works correctly with real dependencies.
These tests require the backend service to be running.
"""

import pytest
import httpx
import asyncio
from unittest.mock import patch
import os

from bff.app.main import create_app
from bff.app.config import BACKEND_BASE_URL


class TestBFFIntegration:
    """Integration tests for BFF service with real backend."""
    
    @pytest.mark.asyncio
    async def test_health_check_with_real_backend(self):
        """Test health check against real backend service."""
        # Skip if backend is not available
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BACKEND_BASE_URL}/healthz", timeout=5.0)
                if response.status_code != 200:
                    pytest.skip("Backend service not available")
        except Exception:
            pytest.skip("Backend service not available")
        
        # Test BFF health check
        app = create_app()
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health")
            
            assert response.status_code == 200
            data = response.json()
            
            assert data["status"] in ["ok", "degraded"]
            assert data["service"] == "hewston-bff"
            assert "backend_api" in data["dependencies"]
            assert data["dependencies"]["backend_api"] in ["ok", "degraded"]
    
    @pytest.mark.asyncio
    async def test_readiness_check_with_real_backend(self):
        """Test readiness check against real backend service."""
        # Skip if backend is not available
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BACKEND_BASE_URL}/healthz", timeout=5.0)
                if response.status_code != 200:
                    pytest.skip("Backend service not available")
        except Exception:
            pytest.skip("Backend service not available")
        
        # Test BFF readiness check
        app = create_app()
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/ready")
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "ready"
    
    def test_bff_service_startup(self):
        """Test that BFF service can start up successfully."""
        app = create_app()
        
        # Verify app is created successfully
        assert app is not None
        assert app.title == "Hewston BFF API"
        assert app.version == "0.1.0"
        
        # Verify routes are registered
        routes = [route.path for route in app.routes]
        assert "/api/v1/health" in routes
        assert "/api/v1/health/ready" in routes
        assert "/api/v1/health/live" in routes
    
    @pytest.mark.asyncio
    async def test_correlation_id_propagation(self):
        """Test that correlation IDs are properly added to responses."""
        app = create_app()
        
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            response = await client.get("/api/v1/health/live")
            
            assert response.status_code == 200
            assert "X-Correlation-ID" in response.headers
            
            correlation_id = response.headers["X-Correlation-ID"]
            assert len(correlation_id) == 32  # UUID hex length
            assert correlation_id.isalnum()  # Should be alphanumeric
    
    @pytest.mark.asyncio
    async def test_concurrent_health_checks(self):
        """Test that BFF can handle concurrent requests."""
        app = create_app()
        
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            # Make 10 concurrent requests
            tasks = [
                client.get("/api/v1/health/live")
                for _ in range(10)
            ]
            
            responses = await asyncio.gather(*tasks)
            
            # All requests should succeed
            for response in responses:
                assert response.status_code == 200
                assert "X-Correlation-ID" in response.headers
            
            # All correlation IDs should be unique
            correlation_ids = [r.headers["X-Correlation-ID"] for r in responses]
            assert len(set(correlation_ids)) == 10  # All unique


class TestBFFConfiguration:
    """Test BFF configuration and environment handling."""
    
    def test_default_configuration(self):
        """Test that BFF uses correct default configuration."""
        from bff.app.config import (
            BFF_DEFAULT_PORT,
            BFF_API_TITLE,
            BFF_API_VERSION,
            BACKEND_BASE_URL,
        )
        
        assert BFF_DEFAULT_PORT == 8001
        assert BFF_API_TITLE == "Hewston BFF API"
        assert BFF_API_VERSION == "0.1.0"
        assert BACKEND_BASE_URL == "http://127.0.0.1:8000"  # Default
    
    def test_environment_variable_override(self):
        """Test that environment variables override default config."""
        with patch.dict(os.environ, {
            "HEWSTON_BACKEND_URL": "http://custom-backend:9000",
            "BFF_LOG_LEVEL": "DEBUG",
        }):
            # Re-import config to pick up environment changes
            import importlib
            from bff.app import config
            importlib.reload(config)
            
            assert config.BACKEND_BASE_URL == "http://custom-backend:9000"
            assert config.LOG_LEVEL == "DEBUG"
    
    def test_feature_flags_configuration(self):
        """Test feature flags configuration."""
        from bff.app.config import FEATURE_FLAGS
        
        # Default feature flags should be enabled
        assert FEATURE_FLAGS["chart_data_aggregation"] is True
        assert FEATURE_FLAGS["run_data_aggregation"] is True
        assert FEATURE_FLAGS["websocket_proxy"] is True
        
        # Caching depends on Redis configuration
        assert "caching_enabled" in FEATURE_FLAGS


class TestBFFProxyIntegration:
    """Test BFF proxy integration with real backend."""

    @pytest.mark.asyncio
    async def test_proxy_endpoints_with_real_backend(self):
        """Test proxy endpoints against real backend service."""
        # Skip if backend is not available
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(f"{BACKEND_BASE_URL}/healthz", timeout=5.0)
                if response.status_code != 200:
                    pytest.skip("Backend service not available")
        except Exception:
            pytest.skip("Backend service not available")

        # Test BFF proxy endpoints
        app = create_app()
        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            # Test backtests list endpoint
            response = await client.get("/api/v1/backtests")
            assert response.status_code == 200
            assert "X-Correlation-ID" in response.headers

            # Test bars endpoint (should handle 404 gracefully if no data)
            response = await client.get("/api/v1/bars/daily?symbol=AAPL")
            assert response.status_code in [200, 404]  # Either data exists or not
            assert "X-Correlation-ID" in response.headers


class TestBFFErrorHandling:
    """Test BFF error handling and resilience."""

    @pytest.mark.asyncio
    async def test_backend_unavailable_handling(self):
        """Test BFF behavior when backend is unavailable."""
        # Override backend URL to point to non-existent service
        with patch("bff.app.config.BACKEND_BASE_URL", "http://localhost:9999"):
            app = create_app()

            async with httpx.AsyncClient(app=app, base_url="http://test") as client:
                # Health check should still respond but show degraded status
                response = await client.get("/api/v1/health")

                assert response.status_code == 200
                data = response.json()

                assert data["status"] == "degraded"
                assert data["dependencies"]["backend_api"] == "down"

                # Readiness check should fail
                response = await client.get("/api/v1/health/ready")
                assert response.status_code == 503

                # Proxy endpoints should return 502 when backend unavailable
                response = await client.get("/api/v1/backtests")
                assert response.status_code == 502
                data = response.json()
                assert data["error"]["code"] == "BACKEND_UNAVAILABLE"

    @pytest.mark.asyncio
    async def test_invalid_request_handling(self):
        """Test BFF handling of invalid requests."""
        app = create_app()

        async with httpx.AsyncClient(app=app, base_url="http://test") as client:
            # Test non-existent endpoint
            response = await client.get("/api/v1/nonexistent")
            assert response.status_code == 404

            # Test invalid method
            response = await client.post("/api/v1/health/live")
            assert response.status_code == 405
