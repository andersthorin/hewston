"""
Backend HTTP Client Service

Provides HTTP client functionality for communicating with the backend API.
Handles request forwarding, authentication pass-through, and error handling.
"""

import httpx
import logging
from typing import Dict, Any, Optional, Union
from fastapi import Request, HTTPException
from fastapi.responses import JSONResponse, Response
import json

from bff.app.config import BACKEND_BASE_URL, BACKEND_TIMEOUT_SECONDS


class BackendClient:
    """HTTP client for backend API communication with proxy functionality."""
    
    def __init__(self, client: httpx.AsyncClient):
        self.client = client
        self.logger = logging.getLogger("bff.backend_client")
    
    async def proxy_request(
        self,
        method: str,
        path: str,
        headers: Optional[Dict[str, str]] = None,
        params: Optional[Dict[str, Any]] = None,
        json_data: Optional[Dict[str, Any]] = None,
        body: Optional[bytes] = None,
        correlation_id: Optional[str] = None,
    ) -> Response:
        """
        Proxy a request to the backend API.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            path: API path (e.g., "/backtests")
            headers: Request headers to forward
            params: Query parameters
            json_data: JSON request body
            body: Raw request body
            correlation_id: Request correlation ID for logging
            
        Returns:
            Response: FastAPI response object
        """
        # Prepare headers for backend request
        backend_headers = self._prepare_headers(headers, correlation_id)
        
        # Log the proxy request
        self.logger.info(
            "proxy.request",
            extra={
                "correlation_id": correlation_id,
                "method": method,
                "path": path,
                "backend_url": BACKEND_BASE_URL,
                "has_body": json_data is not None or body is not None,
            }
        )
        
        try:
            # Make request to backend
            if json_data is not None:
                response = await self.client.request(
                    method=method,
                    url=path,
                    headers=backend_headers,
                    params=params,
                    json=json_data,
                    timeout=BACKEND_TIMEOUT_SECONDS,
                )
            elif body is not None:
                response = await self.client.request(
                    method=method,
                    url=path,
                    headers=backend_headers,
                    params=params,
                    content=body,
                    timeout=BACKEND_TIMEOUT_SECONDS,
                )
            else:
                response = await self.client.request(
                    method=method,
                    url=path,
                    headers=backend_headers,
                    params=params,
                    timeout=BACKEND_TIMEOUT_SECONDS,
                )
            
            # Log the backend response
            self.logger.info(
                "proxy.response",
                extra={
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "status_code": response.status_code,
                    "response_size": len(response.content),
                }
            )
            
            # Return proxied response
            return self._create_response(response, correlation_id)
            
        except httpx.TimeoutException as e:
            self.logger.error(
                "proxy.timeout",
                extra={
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "timeout": BACKEND_TIMEOUT_SECONDS,
                    "error": str(e),
                }
            )
            return JSONResponse(
                status_code=504,
                content={
                    "error": {
                        "code": "BACKEND_TIMEOUT",
                        "message": f"Backend request timed out after {BACKEND_TIMEOUT_SECONDS}s"
                    }
                }
            )
            
        except httpx.ConnectError as e:
            self.logger.error(
                "proxy.connection_error",
                extra={
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "backend_url": BACKEND_BASE_URL,
                    "error": str(e),
                }
            )
            return JSONResponse(
                status_code=502,
                content={
                    "error": {
                        "code": "BACKEND_UNAVAILABLE",
                        "message": "Backend service is unavailable"
                    }
                }
            )
            
        except Exception as e:
            self.logger.exception(
                "proxy.error",
                extra={
                    "correlation_id": correlation_id,
                    "method": method,
                    "path": path,
                    "error": str(e),
                }
            )
            return JSONResponse(
                status_code=500,
                content={
                    "error": {
                        "code": "PROXY_ERROR",
                        "message": "Internal proxy error"
                    }
                }
            )
    
    def _prepare_headers(self, headers: Optional[Dict[str, str]], correlation_id: Optional[str]) -> Dict[str, str]:
        """
        Prepare headers for backend request.
        
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
                    backend_headers[key] = value
        
        # Add BFF identification
        backend_headers["X-Forwarded-By"] = "hewston-bff"
        
        # Add correlation ID for tracing
        if correlation_id:
            backend_headers["X-Correlation-ID"] = correlation_id
        
        return backend_headers
    
    def _create_response(self, backend_response: httpx.Response, correlation_id: Optional[str]) -> Response:
        """
        Create FastAPI response from backend response.
        
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
    """
    Create a BackendClient instance.
    
    Args:
        client: HTTP client for backend communication
        
    Returns:
        BackendClient: Configured backend client
    """
    return BackendClient(client)
