"""
WebSocket Connection Manager

Manages WebSocket connections, subscriptions, and message routing.
Handles connection lifecycle and error recovery.
"""

import asyncio
import json
import logging
from typing import Dict, Set, Optional, Any
from datetime import datetime
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from fastapi import WebSocket, WebSocketDisconnect
from bff.models.websocket import (
    MessageType,
    ConnectionStatus,
    WebSocketMessage,
    SubscribeMessage,
    UnsubscribeMessage,
    ErrorMessage,
    ConnectionStatusMessage,
    PingMessage,
    PongMessage
)
from bff.app.config import BACKEND_BASE_URL


class WebSocketConnectionManager:
    """Manages WebSocket connections and message routing."""
    
    def __init__(self):
        self.logger = logging.getLogger("bff.websocket_manager")
        
        # Client connections: {connection_id: WebSocket}
        self.active_connections: Dict[str, WebSocket] = {}
        
        # Run subscriptions: {run_id: {connection_id}}
        self.run_subscriptions: Dict[str, Set[str]] = {}
        
        # Backend connections: {run_id: backend_websocket}
        self.backend_connections: Dict[str, Any] = {}
        
        # Connection metadata
        self.connection_metadata: Dict[str, Dict[str, Any]] = {}
    
    async def connect_client(self, websocket: WebSocket, connection_id: str) -> None:
        """
        Accept a new client WebSocket connection.
        
        Args:
            websocket: Client WebSocket connection
            connection_id: Unique connection identifier
        """
        await websocket.accept()
        self.active_connections[connection_id] = websocket
        self.connection_metadata[connection_id] = {
            "connected_at": datetime.utcnow().isoformat(),
            "subscriptions": set(),
            "last_ping": None
        }
        
        self.logger.info(
            "client.connected",
            extra={
                "connection_id": connection_id,
                "total_connections": len(self.active_connections),
            }
        )
        
        # Send connection status
        await self._send_to_client(
            connection_id,
            ConnectionStatusMessage(
                status=ConnectionStatus.CONNECTED,
                message="Connected to BFF WebSocket",
                backend_connected=False
            )
        )
    
    async def disconnect_client(self, connection_id: str) -> None:
        """
        Handle client disconnection and cleanup.
        
        Args:
            connection_id: Connection identifier to disconnect
        """
        # Remove from active connections
        if connection_id in self.active_connections:
            del self.active_connections[connection_id]
        
        # Clean up subscriptions
        if connection_id in self.connection_metadata:
            subscriptions = self.connection_metadata[connection_id].get("subscriptions", set())
            # Create a copy to avoid "set changed size during iteration" error
            for run_id in list(subscriptions):
                await self._unsubscribe_from_run(connection_id, run_id)
            del self.connection_metadata[connection_id]
        
        self.logger.info(
            "client.disconnected",
            extra={
                "connection_id": connection_id,
                "total_connections": len(self.active_connections),
            }
        )
    
    async def handle_client_message(
        self,
        connection_id: str,
        message_data: str
    ) -> None:
        """
        Handle incoming message from client.
        
        Args:
            connection_id: Client connection identifier
            message_data: Raw message data
        """
        try:
            message_dict = json.loads(message_data)
            message_type = message_dict.get("type")
            
            self.logger.debug(
                "client.message",
                extra={
                    "connection_id": connection_id,
                    "message_type": message_type,
                }
            )
            
            if message_type == MessageType.SUBSCRIBE:
                await self._handle_subscribe(connection_id, message_dict)
            elif message_type == MessageType.UNSUBSCRIBE:
                await self._handle_unsubscribe(connection_id, message_dict)
            elif message_type == MessageType.PING:
                await self._handle_ping(connection_id, message_dict)
            else:
                await self._send_error(
                    connection_id,
                    "UNKNOWN_MESSAGE_TYPE",
                    f"Unknown message type: {message_type}"
                )
                
        except json.JSONDecodeError as e:
            await self._send_error(
                connection_id,
                "INVALID_JSON",
                f"Invalid JSON message: {str(e)}"
            )
        except Exception as e:
            self.logger.exception(
                "client.message_error",
                extra={
                    "connection_id": connection_id,
                    "error": str(e),
                }
            )
            await self._send_error(
                connection_id,
                "MESSAGE_PROCESSING_ERROR",
                f"Error processing message: {str(e)}"
            )
    
    async def _handle_subscribe(self, connection_id: str, message_dict: Dict[str, Any]) -> None:
        """Handle subscription request."""
        try:
            subscribe_msg = SubscribeMessage(**message_dict)
            run_id = subscribe_msg.run_id
            
            # Add to subscriptions
            if run_id not in self.run_subscriptions:
                self.run_subscriptions[run_id] = set()
            self.run_subscriptions[run_id].add(connection_id)
            
            # Update connection metadata
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["subscriptions"].add(run_id)
            
            # Establish backend connection if needed
            await self._ensure_backend_connection(run_id)
            
            self.logger.info(
                "subscription.added",
                extra={
                    "connection_id": connection_id,
                    "run_id": run_id,
                    "total_subscribers": len(self.run_subscriptions[run_id]),
                }
            )
            
            # Send confirmation
            await self._send_to_client(
                connection_id,
                ConnectionStatusMessage(
                    status=ConnectionStatus.CONNECTED,
                    message=f"Subscribed to run {run_id}",
                    backend_connected=run_id in self.backend_connections
                )
            )
            
        except Exception as e:
            await self._send_error(
                connection_id,
                "SUBSCRIPTION_ERROR",
                f"Error subscribing to run: {str(e)}"
            )
    
    async def _handle_unsubscribe(self, connection_id: str, message_dict: Dict[str, Any]) -> None:
        """Handle unsubscription request."""
        try:
            unsubscribe_msg = UnsubscribeMessage(**message_dict)
            run_id = unsubscribe_msg.run_id
            
            await self._unsubscribe_from_run(connection_id, run_id)
            
            await self._send_to_client(
                connection_id,
                ConnectionStatusMessage(
                    status=ConnectionStatus.CONNECTED,
                    message=f"Unsubscribed from run {run_id}",
                    backend_connected=False
                )
            )
            
        except Exception as e:
            await self._send_error(
                connection_id,
                "UNSUBSCRIPTION_ERROR",
                f"Error unsubscribing from run: {str(e)}"
            )
    
    async def _handle_ping(self, connection_id: str, message_dict: Dict[str, Any]) -> None:
        """Handle ping message."""
        try:
            ping_msg = PingMessage(**message_dict)
            
            # Update last ping time
            if connection_id in self.connection_metadata:
                self.connection_metadata[connection_id]["last_ping"] = ping_msg.timestamp
            
            # Send pong response
            pong_msg = PongMessage(ping_timestamp=ping_msg.timestamp)
            await self._send_to_client(connection_id, pong_msg)
            
        except Exception as e:
            await self._send_error(
                connection_id,
                "PING_ERROR",
                f"Error handling ping: {str(e)}"
            )
    
    async def _ensure_backend_connection(self, run_id: str) -> None:
        """
        Ensure backend WebSocket connection exists for run.
        
        Args:
            run_id: Run identifier
        """
        if run_id in self.backend_connections:
            return  # Already connected
        
        try:
            # Convert HTTP URL to WebSocket URL
            backend_ws_url = BACKEND_BASE_URL.replace("http://", "ws://").replace("https://", "wss://")
            ws_url = f"{backend_ws_url}/backtests/{run_id}/stream"
            
            self.logger.info(
                "backend.connecting",
                extra={
                    "run_id": run_id,
                    "ws_url": ws_url,
                }
            )
            
            # Connect to backend WebSocket
            backend_ws = await websockets.connect(ws_url)
            self.backend_connections[run_id] = backend_ws
            
            # Start message forwarding task
            asyncio.create_task(self._forward_backend_messages(run_id, backend_ws))
            
            self.logger.info(
                "backend.connected",
                extra={
                    "run_id": run_id,
                    "ws_url": ws_url,
                }
            )
            
        except Exception as e:
            self.logger.error(
                "backend.connection_error",
                extra={
                    "run_id": run_id,
                    "error": str(e),
                }
            )
            # Notify subscribers of connection failure
            await self._broadcast_to_run_subscribers(
                run_id,
                ErrorMessage(
                    error_code="BACKEND_CONNECTION_FAILED",
                    error_message=f"Failed to connect to backend for run {run_id}",
                    run_id=run_id
                )
            )
    
    async def _forward_backend_messages(self, run_id: str, backend_ws: Any) -> None:
        """
        Forward messages from backend to subscribed clients.
        
        Args:
            run_id: Run identifier
            backend_ws: Backend WebSocket connection
        """
        try:
            async for message in backend_ws:
                try:
                    # Parse and forward message to subscribers
                    message_dict = json.loads(message)
                    await self._broadcast_to_run_subscribers(run_id, message_dict)
                    
                except json.JSONDecodeError:
                    self.logger.warning(
                        "backend.invalid_message",
                        extra={
                            "run_id": run_id,
                            "message": message,
                        }
                    )
                    
        except ConnectionClosed:
            self.logger.info(
                "backend.disconnected",
                extra={"run_id": run_id}
            )
        except Exception as e:
            self.logger.error(
                "backend.message_error",
                extra={
                    "run_id": run_id,
                    "error": str(e),
                }
            )
        finally:
            # Clean up backend connection
            if run_id in self.backend_connections:
                del self.backend_connections[run_id]
            
            # Notify subscribers of disconnection
            await self._broadcast_to_run_subscribers(
                run_id,
                ConnectionStatusMessage(
                    status=ConnectionStatus.DISCONNECTED,
                    message="Backend connection closed",
                    backend_connected=False
                )
            )
    
    async def _unsubscribe_from_run(self, connection_id: str, run_id: str) -> None:
        """Remove subscription and clean up if needed."""
        # Remove from run subscriptions
        if run_id in self.run_subscriptions:
            self.run_subscriptions[run_id].discard(connection_id)
            
            # If no more subscribers, close backend connection
            if not self.run_subscriptions[run_id]:
                del self.run_subscriptions[run_id]
                if run_id in self.backend_connections:
                    await self.backend_connections[run_id].close()
                    del self.backend_connections[run_id]
        
        # Update connection metadata
        if connection_id in self.connection_metadata:
            self.connection_metadata[connection_id]["subscriptions"].discard(run_id)
    
    async def _broadcast_to_run_subscribers(self, run_id: str, message: Any) -> None:
        """Broadcast message to all subscribers of a run."""
        if run_id not in self.run_subscriptions:
            return
        
        subscribers = self.run_subscriptions[run_id].copy()
        for connection_id in subscribers:
            await self._send_to_client(connection_id, message)
    
    async def _send_to_client(self, connection_id: str, message: Any) -> None:
        """Send message to specific client."""
        if connection_id not in self.active_connections:
            return
        
        try:
            websocket = self.active_connections[connection_id]
            
            # Convert message to JSON
            if hasattr(message, 'model_dump_json'):
                message_json = message.model_dump_json()
            elif hasattr(message, 'json'):
                message_json = message.json()
            else:
                message_json = json.dumps(message)
            
            await websocket.send_text(message_json)
            
        except WebSocketDisconnect:
            await self.disconnect_client(connection_id)
        except Exception as e:
            self.logger.error(
                "client.send_error",
                extra={
                    "connection_id": connection_id,
                    "error": str(e),
                }
            )
            await self.disconnect_client(connection_id)
    
    async def _send_error(self, connection_id: str, error_code: str, error_message: str) -> None:
        """Send error message to client."""
        error_msg = ErrorMessage(
            error_code=error_code,
            error_message=error_message
        )
        await self._send_to_client(connection_id, error_msg)
    
    def get_connection_stats(self) -> Dict[str, Any]:
        """Get connection statistics."""
        return {
            "active_connections": len(self.active_connections),
            "run_subscriptions": len(self.run_subscriptions),
            "backend_connections": len(self.backend_connections),
            "total_subscribers": sum(len(subs) for subs in self.run_subscriptions.values())
        }
