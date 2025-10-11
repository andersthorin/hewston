"""BFF Agentic API proxy routes.

Proxies Agentic Mode endpoints to the backend, preserving request/response
semantics and headers. Canonical paths are exposed under /api/v1/agentic/*.

Endpoints
- POST /agentic/propose_plan { from_date, to_date }
- POST /agentic/start { plan }
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, Depends, Request

from bff.app.dependencies import get_backend_client
from bff.services.backend_client import BackendClient, ProxySpec, create_backend_client

router = APIRouter()
logger = logging.getLogger("bff.agentic")


async def get_correlation_id(request: Request) -> str:
    """Extract correlation ID from request state."""
    return getattr(request.state, "correlation_id", "unknown")


async def get_backend_proxy_client(
    backend_client=Depends(get_backend_client),
) -> BackendClient:
    """Get configured backend proxy client."""
    return await create_backend_client(backend_client)


@router.post("/agentic/propose_plan")
async def proxy_propose_plan(
    request: Request,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """Proxy POST /agentic/propose_plan to backend."""
    try:
        body: dict[str, Any] | None = await request.json()
    except Exception:
        body = None

    return await backend_client.proxy_request(
        ProxySpec(
            method="POST",
            path="/agentic/propose_plan",
            headers=dict(request.headers),
            json_data=body if isinstance(body, dict) else None,
            correlation_id=correlation_id,
        )
    )


@router.post("/agentic/start")
async def proxy_start_agentic(
    request: Request,
    backend_client: BackendClient = Depends(get_backend_proxy_client),
    correlation_id: str = Depends(get_correlation_id),
):
    """Proxy POST /agentic/start to backend."""
    try:
        body: dict[str, Any] | None = await request.json()
    except Exception:
        body = None

    return await backend_client.proxy_request(
        ProxySpec(
            method="POST",
            path="/agentic/start",
            headers=dict(request.headers),
            json_data=body if isinstance(body, dict) else None,
            correlation_id=correlation_id,
        )
    )

