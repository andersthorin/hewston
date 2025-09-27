from fastapi import FastAPI, WebSocket, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time
from uuid import uuid4

from backend.api.routes.health import router as health_router
from backend.api.routes.backtests import router as backtests_router
from backend.api.routes.bars import router as bars_router
from backend.app.logging_setup import configure_logging


def create_app() -> FastAPI:
    configure_logging()
    app = FastAPI(title="Hewston API", version="0.1.0")

    # Local-first defaults; adjust CORS later if needed
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    logger = logging.getLogger(__name__)

    @app.middleware("http")
    async def request_logger(request: Request, call_next):
        req_id = uuid4().hex
        start = time.perf_counter()
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
                },
            )
        except Exception:
            pass
        return response

    # REST routes
    app.include_router(health_router)
    app.include_router(backtests_router)
    app.include_router(bars_router)

    return app


app = create_app()

