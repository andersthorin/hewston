"""
BFF Health Check Endpoint

Enhanced health check that validates BFF service status and dependencies.
Follows the pattern from backend/api/routes/health.py with additional checks.
"""

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Dict, List, Optional, Any
import httpx
import logging
from datetime import datetime, timezone

from bff.app.config import (
    SERVICE_NAME,
    SERVICE_VERSION,
    BUILD_INFO,
    HEALTH_CHECK_DEPENDENCIES,
    BACKEND_BASE_URL,
)
from bff.app.dependencies import get_backend_client, get_redis_client

router = APIRouter()


class HealthStatus(BaseModel):
    """Health check response model."""
    status: str
    service: str
    version: str
    timestamp: str
    dependencies: Dict[str, str]
    build_info: Dict[str, Any]


class DependencyCheck:
    """Helper class for checking service dependencies."""
    
    @staticmethod
    async def check_backend_api(client: httpx.AsyncClient) -> str:
        """
        Check backend API health.
        
        Args:
            client: HTTP client for backend communication
            
        Returns:
            str: Status of backend API ("ok", "degraded", "down")
        """
        try:
            response = await client.get("/healthz", timeout=5.0)
            if response.status_code == 200:
                return "ok"
            else:
                return "degraded"
        except Exception as e:
            logging.warning(f"Backend health check failed: {e}")
            return "down"
    
    @staticmethod
    async def check_redis(redis_client) -> str:
        """
        Check Redis connection.
        
        Args:
            redis_client: Redis client instance
            
        Returns:
            str: Status of Redis ("ok", "down", "disabled")
        """
        if redis_client is None:
            return "disabled"
        
        try:
            await redis_client.ping()
            return "ok"
        except Exception as e:
            logging.warning(f"Redis health check failed: {e}")
            return "down"


@router.get("/health", response_model=HealthStatus)
async def health_check(
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
    redis_client = Depends(get_redis_client),
) -> HealthStatus:
    """
    Comprehensive health check for BFF service.
    
    Validates:
    - BFF service status
    - Backend API connectivity
    - Redis connectivity (if enabled)
    - Service configuration
    
    Returns:
        HealthStatus: Detailed health information
    """
    logger = logging.getLogger("bff.health")
    
    # Check all dependencies
    dependency_status = {}
    overall_status = "ok"
    
    # Check backend API
    if "backend_api" in HEALTH_CHECK_DEPENDENCIES:
        backend_status = await DependencyCheck.check_backend_api(backend_client)
        dependency_status["backend_api"] = backend_status
        
        if backend_status == "down":
            overall_status = "degraded"
        elif backend_status == "degraded" and overall_status == "ok":
            overall_status = "degraded"
    
    # Check Redis
    if "redis" in HEALTH_CHECK_DEPENDENCIES:
        redis_status = await DependencyCheck.check_redis(redis_client)
        dependency_status["redis"] = redis_status
        
        # Redis is optional, so don't fail health check if it's down
        if redis_status == "down":
            logger.warning("Redis is down but health check continues (optional dependency)")
    
    # Log health check result
    logger.info(
        "health.check",
        extra={
            "status": overall_status,
            "dependencies": dependency_status,
            "service": SERVICE_NAME,
        }
    )
    
    return HealthStatus(
        status=overall_status,
        service=SERVICE_NAME,
        version=SERVICE_VERSION,
        timestamp=datetime.now(timezone.utc).isoformat(),
        dependencies=dependency_status,
        build_info=BUILD_INFO,
    )


@router.get("/health/ready")
async def readiness_check(
    backend_client: httpx.AsyncClient = Depends(get_backend_client),
) -> Dict[str, str]:
    """
    Kubernetes-style readiness check.
    
    Returns 200 if service is ready to accept traffic, 503 otherwise.
    """
    # Check critical dependencies only
    backend_status = await DependencyCheck.check_backend_api(backend_client)
    
    if backend_status == "down":
        raise HTTPException(
            status_code=503,
            detail="Service not ready - backend API unavailable"
        )
    
    return {"status": "ready"}


@router.get("/health/live")
async def liveness_check() -> Dict[str, str]:
    """
    Kubernetes-style liveness check.
    
    Returns 200 if service is alive, 503 if it should be restarted.
    """
    # Simple liveness check - if we can respond, we're alive
    return {"status": "alive"}
