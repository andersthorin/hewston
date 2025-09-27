"""
BFF Test Configuration

Provides test fixtures and configuration for BFF service testing.
"""

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock
import httpx

from bff.app.main import create_app
from bff.app.dependencies import get_backend_client, get_redis_client
from bff.services.backend_client import create_backend_client


@pytest.fixture
def mock_backend_client():
    """Mock backend HTTP client for testing."""
    mock_client = AsyncMock(spec=httpx.AsyncClient)
    
    # Default successful health check response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}
    mock_client.get.return_value = mock_response
    
    return mock_client


@pytest.fixture
def mock_redis_client():
    """Mock Redis client for testing."""
    mock_client = AsyncMock()
    mock_client.ping.return_value = True
    return mock_client


@pytest.fixture
def test_app(mock_backend_client, mock_redis_client):
    """Create test FastAPI app with mocked dependencies."""
    app = create_app()

    # Override dependencies with mocks
    app.dependency_overrides[get_backend_client] = lambda: mock_backend_client
    app.dependency_overrides[get_redis_client] = lambda: mock_redis_client

    return app


@pytest.fixture
def mock_backend_response():
    """Create a mock backend response that works with the proxy client."""
    def _create_response(status_code=200, data=None):
        mock_response = MagicMock()
        mock_response.status_code = status_code

        if data:
            import json
            response_content = json.dumps(data).encode()
            mock_response.content = response_content
            mock_response.body = response_content  # For backward compatibility
        else:
            mock_response.content = b""
            mock_response.body = b""

        return mock_response

    return _create_response


@pytest.fixture
def test_client(test_app):
    """Create test client for BFF service."""
    return TestClient(test_app)


@pytest_asyncio.fixture
async def async_test_client(test_app):
    """Create async test client for BFF service."""
    async with httpx.AsyncClient(app=test_app, base_url="http://test") as client:
        yield client


@pytest.fixture
def mock_backend_proxy_client(mock_backend_client):
    """Mock backend proxy client for testing."""
    async def _create_mock_backend_client():
        from bff.services.backend_client import BackendClient
        return BackendClient(mock_backend_client)

    return _create_mock_backend_client
