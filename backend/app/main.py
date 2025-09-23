from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from backend.api.routes.health import router as health_router
from backend.api.routes.backtests import router as backtests_router


def create_app() -> FastAPI:
    app = FastAPI(title="Hewston API", version="0.1.0")

    # Local-first defaults; adjust CORS later if needed
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # REST routes
    app.include_router(health_router)
    app.include_router(backtests_router)

    return app


app = create_app()

