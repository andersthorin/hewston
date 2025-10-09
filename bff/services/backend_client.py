"""Backend HTTP Client Service.

Provides HTTP client functionality for communicating with the backend API.
Handles request forwarding, authentication pass-through, and error handling.
"""

import json
import logging
from dataclasses import dataclass
from typing import Any

import httpx
from fastapi.responses import JSONResponse, Response

from bff.app.config import BACKEND_BASE_URL, BACKEND_TIMEOUT_SECONDS


@dataclass(frozen=True)
class ProxySpec:
    """Specification for a backend proxy request."""

    method: str
    path: str
    headers: dict[str, str] | None = None
    params: dict[str, Any] | None = None
    json_data: dict[str, Any] | None = None
    body: bytes | None = None
    correlation_id: str | None = None


class BackendClient:
    """HTTP client for backend API communication with proxy functionality."""

    def __init__(self, client: httpx.AsyncClient):
        """Initialize the backend client with an AsyncClient."""
        self.client = client
        self.logger = logging.getLogger("bff.backend_client")

    async def proxy_request(self, spec: ProxySpec | None = None, **kwargs) -> Response:
        """Proxy a request to the backend API.

        Backward-compatible signature: callers may either pass a ProxySpec instance
        or use keyword arguments (method, path, headers, params, json_data, body,
        correlation_id).

        Args:
            spec: Complete request specification. If None, it will be built from kwargs.
            **kwargs: Backward-compatible alternative to provide individual fields
                when ``spec`` is not supplied. Supported keys are: ``method``,
                ``path``, ``headers``, ``params``, ``json_data``, ``body``,
                ``correlation_id``.

        Returns:
            Response: FastAPI response object
        """
        # Build spec from kwargs for backward compatibility with existing callers
        if spec is None:
            if "path" not in kwargs:
                raise ValueError(
                    "proxy_request requires either a ProxySpec or keyword args including 'path'"
                )
            spec = ProxySpec(
                method=str(kwargs.get("method") or "GET").upper(),
                path=str(kwargs.get("path")),
                headers=kwargs.get("headers"),
                params=kwargs.get("params"),
                json_data=kwargs.get("json_data"),
                body=kwargs.get("body"),
                correlation_id=kwargs.get("correlation_id"),
            )

        # Prepare headers for backend request
        backend_headers = self._prepare_headers(spec.headers, spec.correlation_id)

        # Log the proxy request
        self.logger.info(
            "proxy.request",
            extra={
                "correlation_id": spec.correlation_id,
                "method": spec.method,
                "path": spec.path,
                "backend_url": BACKEND_BASE_URL,
                "has_body": spec.json_data is not None or spec.body is not None,
            },
        )

        try:
            # Make request to backend
            if spec.json_data is not None:
                response = await self.client.request(
                    method=spec.method,
                    url=spec.path,
                    headers=backend_headers,
                    params=spec.params,
                    json=spec.json_data,
                    timeout=BACKEND_TIMEOUT_SECONDS,
                )
            elif spec.body is not None:
                response = await self.client.request(
                    method=spec.method,
                    url=spec.path,
                    headers=backend_headers,
                    params=spec.params,
                    content=spec.body,
                    timeout=BACKEND_TIMEOUT_SECONDS,
                )
            else:
                response = await self.client.request(
                    method=spec.method,
                    url=spec.path,
                    headers=backend_headers,
                    params=spec.params,
                    timeout=BACKEND_TIMEOUT_SECONDS,
                )

            # Log the backend response
            self.logger.info(
                "proxy.response",
                extra={
                    "correlation_id": spec.correlation_id,
                    "method": spec.method,
                    "path": spec.path,
                    "status_code": response.status_code,
                    "response_size": len(response.content),
                },
            )

            # Return proxied response
            return self._create_response(response, spec.correlation_id)

        except httpx.TimeoutException as e:
            self.logger.error(
                "proxy.timeout",
                extra={
                    "correlation_id": spec.correlation_id,
                    "method": spec.method,
                    "path": spec.path,
                    "timeout": BACKEND_TIMEOUT_SECONDS,
                    "error": str(e),
                },
            )
            return JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "code": "BACKEND_TIMEOUT",
                        "message": f"Backend request timed out after {BACKEND_TIMEOUT_SECONDS}s",
                    }
                },
            )

        except httpx.ConnectError as e:
            self.logger.error(
                "proxy.connection_error",
                extra={
                    "correlation_id": spec.correlation_id,
                    "method": spec.method,
                    "path": spec.path,
                    "backend_url": BACKEND_BASE_URL,
                    "error": str(e),
                },
            )
            return JSONResponse(
                status_code=502,
                content={
                    "error": {
                        "code": "BACKEND_UNAVAILABLE",
                        "message": "Backend service is unavailable",
                    }
                },
            )

        except Exception as e:
            self.logger.exception(
                "proxy.error",
                extra={
                    "correlation_id": spec.correlation_id,
                    "method": spec.method,
                    "path": spec.path,
                    "error": str(e),
                },
            )
            return JSONResponse(
                status_code=500,
                content={"error": {"code": "PROXY_ERROR", "message": "Internal proxy error"}},
            )

    def _prepare_headers(
        self,
        headers: dict[str, str] | None,
        correlation_id: str | None,
    ) -> dict[str, str]:
        """Prepare headers for backend request.

        Args:
            headers: Original request headers
            correlation_id: Request correlation ID

        Returns:
            Dict[str, str]: Headers to send to backend
        """
        backend_headers = {}

        if headers:
            # Forward important headers
            headers_to_forward = {
                "authorization",
                "content-type",
                "accept",
                "user-agent",
                "idempotency-key",
            }

            for key, value in headers.items():
                if key.lower() in headers_to_forward:
                    # Normalize forwarded header keys to lowercase for consistency/tests
                    backend_headers[key.lower()] = value

        # Add BFF identification
        backend_headers["X-Forwarded-By"] = "hewston-bff"

        # Add correlation ID for tracing
        if correlation_id:
            backend_headers["X-Correlation-ID"] = correlation_id

        return backend_headers

    def _create_response(
        self, backend_response: httpx.Response, correlation_id: str | None
    ) -> Response:
        """Create FastAPI response from backend response.

        Args:
            backend_response: Response from backend
            correlation_id: Request correlation ID

        Returns:
            Response: FastAPI response object
        """
        # Determine content type
        content_type = backend_response.headers.get("content-type", "application/json")

        # Prepare response headers
        response_headers = {}

        # Forward important response headers
        headers_to_forward = {
            "content-type",
            "cache-control",
            "etag",
            "last-modified",
        }

        for key, value in backend_response.headers.items():
            if key.lower() in headers_to_forward:
                response_headers[key] = value

        # Add correlation ID to response
        if correlation_id:
            response_headers["X-Correlation-ID"] = correlation_id

        # Create appropriate response based on content type
        if "application/json" in content_type:
            try:
                # Parse and re-serialize JSON to ensure valid format
                json_content = backend_response.json()
                return JSONResponse(
                    content=json_content,
                    status_code=backend_response.status_code,
                    headers=response_headers,
                )
            except json.JSONDecodeError:
                # Fallback to raw content if JSON parsing fails
                pass

        # Return raw response for non-JSON content
        return Response(
            content=backend_response.content,
            status_code=backend_response.status_code,
            headers=response_headers,
            media_type=content_type,
        )


async def create_backend_client(client: httpx.AsyncClient) -> BackendClient:
    """Create and return a configured BackendClient instance.

    Args:
        client: HTTP client for backend communication

    Returns:
        BackendClient: Configured backend client
    """
    return BackendClient(client)
