"""
BFF FastAPI Application

Main application factory for the Backend-for-Frontend service.
Follows the pattern established in backend/app/main.py with BFF-specific enhancements.
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from uuid import uuid4
from contextlib import asynccontextmanager

from bff.api.health import router as health_router
from bff.api.proxy import router as proxy_router
from bff.api.chart_data import router as chart_data_router
from bff.api.run_data import router as run_data_router
from bff.api.websocket import router as websocket_router
from bff.app.config import (
    BFF_API_TITLE,
    BFF_API_VERSION,
    BFF_API_DESCRIPTION,
    BFF_CORS_ORIGINS,
    LOG_LEVEL,
)
from bff.app.dependencies import cleanup_dependencies
from backend.app.logging_setup import configure_logging


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager for startup and shutdown events.
    """
    # Startup
    logger = logging.getLogger("bff.startup")
    logger.info("BFF service starting up", extra={"service": "hewston-bff"})
    
    yield
    
    # Shutdown
    logger.info("BFF service shutting down", extra={"service": "hewston-bff"})
    await cleanup_dependencies()


def create_app() -> FastAPI:
    """
    Create and configure the BFF FastAPI application.
    
    Returns:
        FastAPI: Configured application instance
    """
    # Configure logging using existing backend patterns
    log_level = getattr(logging, LOG_LEVEL.upper(), logging.INFO)
    configure_logging(level=log_level)
    
    # Create FastAPI app with lifespan management
    app = FastAPI(
        title=BFF_API_TITLE,
        version=BFF_API_VERSION,
        description=BFF_API_DESCRIPTION,
        lifespan=lifespan,
    )

    # CORS middleware - same as backend for consistency
    app.add_middleware(
        CORSMiddleware,
        allow_origins=BFF_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger = logging.getLogger("bff")

    @app.middleware("http")
    async def request_logger(request: Request, call_next):
        """
        Request logging middleware following backend patterns.
        Adds correlation ID and timing information.
        """
        req_id = uuid4().hex
        start = time.perf_counter()
        
        # Add correlation ID to request state for downstream use
        request.state.correlation_id = req_id
        
        response = await call_next(request)
        
        dur_ms = int((time.perf_counter() - start) * 1000)
        
        try:
            logger.info(
                "http.access",
                extra={
                    "request_id": req_id,
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "latency_ms": dur_ms,
                    "service": "bff",
                },
            )
        except Exception:
            # Don't let logging errors break the request
            pass
        
        # Add correlation ID to response headers for debugging
        response.headers["X-Correlation-ID"] = req_id
        
        return response

    # Include API routes
    app.include_router(health_router, prefix="/api/v1")
    app.include_router(proxy_router, prefix="/api/v1")
    app.include_router(chart_data_router, prefix="/api/v1")
    app.include_router(run_data_router, prefix="/api/v1")
    app.include_router(websocket_router, prefix="/api/v1")

    return app


# Create the application instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    from bff.app.config import BFF_DEFAULT_HOST, BFF_DEFAULT_PORT
    
    uvicorn.run(
        "bff.app.main:app",
        host=BFF_DEFAULT_HOST,
        port=BFF_DEFAULT_PORT,
        reload=True,
        log_config=None,  # Use our custom logging
    )
