"""
WebSocket API

Provides WebSocket endpoints for real-time communication with backend services.
Handles run streaming, connection management, and message routing.
"""

import uuid
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Path, Depends
from typing import Optional

from bff.services.websocket_manager import WebSocketConnectionManager
from bff.models.websocket import ConnectionStatus, ConnectionStatusMessage

router = APIRouter()
logger = logging.getLogger("bff.websocket_api")

# Global connection manager instance
connection_manager = WebSocketConnectionManager()


@router.websocket("/runs/{run_id}/stream")
async def websocket_run_stream(
    websocket: WebSocket,
    run_id: str = Path(..., description="Run identifier to stream")
):
    """
    WebSocket endpoint for real-time run updates.
    
    Provides bidirectional communication for run status, metrics,
    and order updates. Automatically subscribes to the specified run.
    
    Args:
        websocket: WebSocket connection
        run_id: Run identifier to stream updates for
    """
    connection_id = str(uuid.uuid4())
    
    logger.info(
        "websocket.connection_request",
        extra={
            "connection_id": connection_id,
            "run_id": run_id,
            "client_host": websocket.client.host if websocket.client else "unknown",
        }
    )
    
    try:
        # Accept connection
        await connection_manager.connect_client(websocket, connection_id)
        
        # Auto-subscribe to the run
        subscribe_message = {
            "type": "subscribe",
            "run_id": run_id,
            "updates": ["run_status", "metrics", "orders"]
        }
        await connection_manager.handle_client_message(
            connection_id,
            str(subscribe_message).replace("'", '"')
        )
        
        logger.info(
            "websocket.connected",
            extra={
                "connection_id": connection_id,
                "run_id": run_id,
            }
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
                    }
                )
                break
                
            except Exception as e:
                logger.error(
                    "websocket.message_error",
                    extra={
                        "connection_id": connection_id,
                        "run_id": run_id,
                        "error": str(e),
                    }
                )
                # Send error to client but continue connection
                await connection_manager._send_error(
                    connection_id,
                    "MESSAGE_ERROR",
                    f"Error processing message: {str(e)}"
                )
                
    except Exception as e:
        logger.exception(
            "websocket.connection_error",
            extra={
                "connection_id": connection_id,
                "run_id": run_id,
                "error": str(e),
            }
        )
    finally:
        # Clean up connection
        await connection_manager.disconnect_client(connection_id)
        
        logger.info(
            "websocket.disconnected",
            extra={
                "connection_id": connection_id,
                "run_id": run_id,
            }
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
        }
    )
    
    try:
        # Accept connection
        await connection_manager.connect_client(websocket, connection_id)
        
        logger.info(
            "websocket.general_connected",
            extra={"connection_id": connection_id}
        )
        
        # Handle incoming messages
        while True:
            try:
                message = await websocket.receive_text()
                await connection_manager.handle_client_message(connection_id, message)
                
            except WebSocketDisconnect:
                logger.info(
                    "websocket.general_client_disconnect",
                    extra={"connection_id": connection_id}
                )
                break
                
            except Exception as e:
                logger.error(
                    "websocket.general_message_error",
                    extra={
                        "connection_id": connection_id,
                        "error": str(e),
                    }
                )
                # Send error to client but continue connection
                await connection_manager._send_error(
                    connection_id,
                    "MESSAGE_ERROR",
                    f"Error processing message: {str(e)}"
                )
                
    except Exception as e:
        logger.exception(
            "websocket.general_connection_error",
            extra={
                "connection_id": connection_id,
                "error": str(e),
            }
        )
    finally:
        # Clean up connection
        await connection_manager.disconnect_client(connection_id)
        
        logger.info(
            "websocket.general_disconnected",
            extra={"connection_id": connection_id}
        )


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
    
    logger.info(
        "websocket.stats_request",
        extra=stats
    )
    
    return {
        "websocket_stats": stats,
        "timestamp": "2024-01-01T00:00:00Z"  # Would use actual timestamp
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
            "timestamp": "2024-01-01T00:00:00Z"
        }
        
    except Exception as e:
        logger.error(
            "websocket.health_error",
            extra={"error": str(e)}
        )
        
        return {
            "status": "unhealthy",
            "service": "websocket",
            "error": str(e),
            "timestamp": "2024-01-01T00:00:00Z"
        }
