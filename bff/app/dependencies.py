"""BFF dependency injection.

Provides dependency injection for BFF services, following FastAPI patterns
and enabling easy testing and configuration management.
"""

import asyncio
import logging
import time
from contextlib import suppress

import httpx
from fastapi import Depends

from bff.app import config

# Global HTTP client for backend communication
_backend_client: httpx.AsyncClient | None = None
# Track the event loop that created the client to avoid cross-loop reuse in tests
_backend_client_loop_id: int | None = None
# Track the base URL used to construct the client so patched configs take effect in tests
_backend_client_base_url: str | None = None

# Global Redis client (if enabled)
_redis_client = None
# Circuit breaker timestamp (epoch seconds) to avoid repeated slow connection attempts
_redis_disabled_until: float = 0.0


async def get_backend_client() -> httpx.AsyncClient:
    """Get async HTTP client for backend communication.

    Returns:
        httpx.AsyncClient: Configured client for backend API calls
    """
    global _backend_client, _backend_client_loop_id, _backend_client_base_url

    current_loop = asyncio.get_running_loop()
    current_loop_id = id(current_loop)
    # Normalize backend base URL to include canonical API prefix
    raw_base_url = config.BACKEND_BASE_URL  # read at call time so test patches take effect
    desired_base_url = raw_base_url.rstrip("/")
    if not desired_base_url.endswith("/api/v1"):
        desired_base_url = desired_base_url + "/api/v1"

    # Recreate client if it does not exist, is bound to a different loop, or base URL changed
    needs_new = (
        _backend_client is None
        or _backend_client_loop_id != current_loop_id
        or _backend_client_base_url != desired_base_url
    )

    if needs_new:
        # Close existing client if present
        if _backend_client is not None:
            with suppress(Exception):
                await _backend_client.aclose()
        _backend_client = httpx.AsyncClient(
            base_url=desired_base_url,
            timeout=httpx.Timeout(config.BACKEND_TIMEOUT_SECONDS),
            headers={
                "User-Agent": "Hewston-BFF/0.1.0",
            },
        )
        _backend_client_loop_id = current_loop_id
        _backend_client_base_url = desired_base_url

    return _backend_client


async def get_redis_client():
    """Get Redis client for caching (if enabled), with fast-fail and circuit breaker.

    Returns:
        Redis client or None if Redis is disabled/unavailable
    """
    global _redis_client, _redis_disabled_until

    if not config.REDIS_ENABLED:
        return None

    # Circuit breaker: if we recently failed, skip reconnect attempts for a while
    now = time.time()
    if _redis_disabled_until and now < _redis_disabled_until:
        return None

    if _redis_client is None:
        try:
            import redis.asyncio as redis

            # Use very short socket timeouts to avoid 30s hangs when Redis is unreachable
            _redis_client = redis.from_url(
                config.REDIS_URL,
                socket_connect_timeout=0.2,
                socket_timeout=0.2,
                retry_on_timeout=False,
            )
            # Quick ping to verify connectivity with hard timeout guard
            try:
                await asyncio.wait_for(_redis_client.ping(), timeout=0.25)
            except TimeoutError as err:
                raise TimeoutError("Redis ping timeout") from err
        except ImportError:
            logging.warning("Redis not available - install redis package for caching")
            # Back off longer if package is missing
            _redis_disabled_until = now + 1800  # 30 minutes
            return None
        except Exception as e:
            logging.warning(f"Redis connection failed: {e}")
            # Back off for a short period to avoid per-request stalls
            _redis_disabled_until = now + 300  # 5 minutes
            _redis_client = None
            return None

    return _redis_client


async def get_logger() -> logging.Logger:
    """Get configured logger for BFF operations.

    Returns:
        logging.Logger: Configured logger instance
    """
    return logging.getLogger("bff")


# Dependency functions for FastAPI
BackendClient = Depends(get_backend_client)
RedisClient = Depends(get_redis_client)
Logger = Depends(get_logger)


async def cleanup_dependencies():
    """Close client connections on shutdown."""
    global _backend_client, _redis_client

    if _backend_client:
        await _backend_client.aclose()
        _backend_client = None

    if _redis_client:
        await _redis_client.close()
        _redis_client = None
