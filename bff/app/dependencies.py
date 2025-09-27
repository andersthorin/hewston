"""
BFF Dependency Injection

Provides dependency injection for BFF services, following FastAPI patterns
and enabling easy testing and configuration management.
"""

from typing import Optional
import httpx
import logging
from fastapi import Depends

from bff.app.config import (
    BACKEND_BASE_URL,
    BACKEND_TIMEOUT_SECONDS,
    REDIS_ENABLED,
    REDIS_URL,
)

# Global HTTP client for backend communication
_backend_client: Optional[httpx.AsyncClient] = None

# Global Redis client (if enabled)
_redis_client = None


async def get_backend_client() -> httpx.AsyncClient:
    """
    Get async HTTP client for backend communication.
    
    Returns:
        httpx.AsyncClient: Configured client for backend API calls
    """
    global _backend_client
    
    if _backend_client is None:
        _backend_client = httpx.AsyncClient(
            base_url=BACKEND_BASE_URL,
            timeout=httpx.Timeout(BACKEND_TIMEOUT_SECONDS),
            headers={
                "User-Agent": "Hewston-BFF/0.1.0",
            }
        )
    
    return _backend_client


async def get_redis_client():
    """
    Get Redis client for caching (if enabled).
    
    Returns:
        Redis client or None if Redis is disabled
    """
    global _redis_client
    
    if not REDIS_ENABLED:
        return None
    
    if _redis_client is None:
        try:
            import redis.asyncio as redis
            _redis_client = redis.from_url(REDIS_URL)
            # Test connection
            await _redis_client.ping()
        except ImportError:
            logging.warning("Redis not available - install redis package for caching")
            return None
        except Exception as e:
            logging.warning(f"Redis connection failed: {e}")
            return None
    
    return _redis_client


async def get_logger() -> logging.Logger:
    """
    Get configured logger for BFF operations.
    
    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger("bff")


# Dependency functions for FastAPI
BackendClient = Depends(get_backend_client)
RedisClient = Depends(get_redis_client)
Logger = Depends(get_logger)


async def cleanup_dependencies():
    """
    Cleanup function to close connections on shutdown.
    """
    global _backend_client, _redis_client
    
    if _backend_client:
        await _backend_client.aclose()
        _backend_client = None
    
    if _redis_client:
        await _redis_client.close()
        _redis_client = None
