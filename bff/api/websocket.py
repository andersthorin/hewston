"""
WebSocket API

Provides WebSocket endpoints for real-time communication with backend services.
Handles run streaming, connection management, and message routing.
"""

import json
import logging
import uuid

from fastapi import APIRouter, Path, WebSocket, WebSocketDisconnect

from bff.services.websocket_manager import WebSocketConnectionManager

router = APIRouter()
logger = logging.getLogger("bff.websocket_api")

# Global connection manager instance
connection_manager = WebSocketConnectionManager()


@router.websocket("/backtests/{backtest_id}/stream")
async def websocket_backtest_stream(
    websocket: WebSocket, backtest_id: str = Path(..., description="Backtest identifier to stream")
):
    """
    WebSocket endpoint for real-time backtest updates (canonical).

    Provides bidirectional communication for backtest status, metrics,
    and order updates. Automatically subscribes to the specified backtest.
    """
    connection_id = str(uuid.uuid4())
    run_id = backtest_id

    logger.info(
        "websocket.connection_request",
        extra={
            "connection_id": connection_id,
            "run_id": run_id,
            "client_host": websocket.client.host if websocket.client else "unknown",
        },
    )

    try:
        # Accept connection
        await connection_manager.connect_client(websocket, connection_id)

        # Auto-subscribe to the backtest
        subscribe_message = {
            "type": "subscribe",
            "run_id": run_id,
            "updates": ["run_status", "metrics", "orders"],
        }
        await connection_manager.handle_client_message(connection_id, json.dumps(subscribe_message))

        logger.info(
            "websocket.connected",
            extra={
                "connection_id": connection_id,
                "run_id": run_id,
            },
        )

        # Handle incoming messages
        while True:
            try:
                message = await websocket.receive_text()
                await connection_manager.handle_client_message(connection_id, message)

            except WebSocketDisconnect:
                logger.info(
                    "websocket.client_disconnect",
                    extra={
                        "connection_id": connection_id,
                        "run_id": run_id,
                    },
                )
                break

            except Exception as e:
                # Minimal guard: if socket not connected/accepted, stop silently
                try:
                    from starlette.websockets import WebSocketState

                    if getattr(websocket, "application_state", None) != WebSocketState.CONNECTED:
                        break
                except Exception:
                    pass
                msg = str(e)

                # Log non-connection errors and attempt a single error reply
                logger.error(
                    f"websocket.message_error: {msg}",
                    extra={
                        "connection_id": connection_id,
                        "run_id": run_id,
                        "error": msg,
                        "error_type": type(e).__name__,
                    },
                )

                if not isinstance(e, ConnectionResetError | BrokenPipeError | OSError):
                    try:
                        await connection_manager._send_error(
                            connection_id, "MESSAGE_ERROR", f"Error processing message: {msg}"
                        )
                    except Exception as send_error:
                        logger.debug(
                            "websocket.error_response_failed",
                            extra={
                                "connection_id": connection_id,
                                "run_id": run_id,
                                "original_error": msg,
                                "send_error": str(send_error),
                            },
                        )
                break

    except Exception as e:
        logger.exception(
            "websocket.connection_error",
            extra={
                "connection_id": connection_id,
                "run_id": run_id,
                "error": str(e),
            },
        )
    finally:
        # Clean up connection
        await connection_manager.disconnect_client(connection_id)

        logger.info(
            "websocket.disconnected",
            extra={
                "connection_id": connection_id,
                "run_id": run_id,
            },
        )


@router.websocket("/stream")
async def websocket_general_stream(websocket: WebSocket):
    """
    General WebSocket endpoint for multi-run streaming.

    Allows clients to subscribe/unsubscribe to multiple runs
    dynamically through message-based control.

    Args:
        websocket: WebSocket connection
    """
    connection_id = str(uuid.uuid4())

    logger.info(
        "websocket.general_connection_request",
        extra={
            "connection_id": connection_id,
            "client_host": websocket.client.host if websocket.client else "unknown",
        },
    )

    try:
        # Accept connection
        await connection_manager.connect_client(websocket, connection_id)

        logger.info("websocket.general_connected", extra={"connection_id": connection_id})

        # Handle incoming messages
        while True:
            try:
                message = await websocket.receive_text()
                await connection_manager.handle_client_message(connection_id, message)

            except WebSocketDisconnect:
                logger.info(
                    "websocket.general_client_disconnect", extra={"connection_id": connection_id}
                )
                break

            except Exception as e:
                # Minimal guard: if socket not connected/accepted, stop silently
                try:
                    from starlette.websockets import WebSocketState

                    if getattr(websocket, "application_state", None) != WebSocketState.CONNECTED:
                        break
                except Exception:
                    pass
                msg = str(e)

                logger.error(
                    f"websocket.general_message_error: {msg}",
                    extra={
                        "connection_id": connection_id,
                        "error": msg,
                        "error_type": type(e).__name__,
                    },
                )

                if not isinstance(e, ConnectionResetError | BrokenPipeError | OSError):
                    try:
                        await connection_manager._send_error(
                            connection_id, "MESSAGE_ERROR", f"Error processing message: {msg}"
                        )
                    except Exception as send_error:
                        logger.debug(
                            "websocket.general_error_response_failed",
                            extra={
                                "connection_id": connection_id,
                                "original_error": msg,
                                "send_error": str(send_error),
                            },
                        )
                break

    except Exception as e:
        logger.exception(
            "websocket.general_connection_error",
            extra={
                "connection_id": connection_id,
                "error": str(e),
            },
        )
    finally:
        # Clean up connection
        await connection_manager.disconnect_client(connection_id)

        logger.info("websocket.general_disconnected", extra={"connection_id": connection_id})


@router.get("/websocket/stats")
async def get_websocket_stats():
    """
    Get WebSocket connection statistics.

    Returns information about active connections, subscriptions,
    and backend connections for monitoring purposes.

    Returns:
        Dict: WebSocket statistics
    """
    stats = connection_manager.get_connection_stats()

    logger.info("websocket.stats_request", extra=stats)

    return {
        "websocket_stats": stats,
        "timestamp": "2024-01-01T00:00:00Z",  # Would use actual timestamp
    }


# Health check endpoint for WebSocket service
@router.get("/websocket/health")
async def websocket_health():
    """
    WebSocket service health check.

    Returns the health status of the WebSocket service
    and connection manager.

    Returns:
        Dict: Health status
    """
    try:
        stats = connection_manager.get_connection_stats()

        return {
            "status": "healthy",
            "service": "websocket",
            "active_connections": stats["active_connections"],
            "backend_connections": stats["backend_connections"],
            "timestamp": "2024-01-01T00:00:00Z",
        }

    except Exception as e:
        logger.error("websocket.health_error", extra={"error": str(e)})

        return {
            "status": "unhealthy",
            "service": "websocket",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z",
        }
