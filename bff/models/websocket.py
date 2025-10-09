"""WebSocket models.

Pydantic models for WebSocket communication and message handling.
"""

from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class MessageType(str, Enum):
    """WebSocket message types."""

    # Client to server messages
    SUBSCRIBE = "subscribe"
    UNSUBSCRIBE = "unsubscribe"
    PING = "ping"

    # Server to client messages
    RUN_UPDATE = "run_update"
    METRICS_UPDATE = "metrics_update"
    ORDER_UPDATE = "order_update"
    ERROR = "error"
    PONG = "pong"
    CONNECTION_STATUS = "connection_status"


class ConnectionStatus(str, Enum):
    """WebSocket connection status."""

    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    RECONNECTING = "reconnecting"


class WebSocketMessage(BaseModel):
    """Base WebSocket message structure."""

    type: MessageType = Field(..., description="Message type")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="Message timestamp"
    )
    correlation_id: str | None = Field(default=None, description="Request correlation ID")
    data: dict[str, Any] | None = Field(default=None, description="Message payload")


class SubscribeMessage(BaseModel):
    """Subscribe to run updates message."""

    type: MessageType = Field(default=MessageType.SUBSCRIBE, description="Message type")
    run_id: str = Field(..., description="Run ID to subscribe to")
    updates: list[str] | None = Field(
        default=["run_status", "metrics", "orders"], description="Types of updates to receive"
    )


class UnsubscribeMessage(BaseModel):
    """Unsubscribe from run updates message."""

    type: MessageType = Field(default=MessageType.UNSUBSCRIBE, description="Message type")
    run_id: str = Field(..., description="Run ID to unsubscribe from")


class RunUpdateMessage(BaseModel):
    """Run status update message."""

    type: MessageType = Field(default=MessageType.RUN_UPDATE, description="Message type")
    run_id: str = Field(..., description="Run ID")
    status: str = Field(..., description="Current run status")
    progress: float | None = Field(default=None, description="Progress percentage (0-100)")
    message: str | None = Field(default=None, description="Status message")
    updated_at: str = Field(..., description="Update timestamp")


class MetricsUpdateMessage(BaseModel):
    """Metrics update message."""

    type: MessageType = Field(default=MessageType.METRICS_UPDATE, description="Message type")
    run_id: str = Field(..., description="Run ID")
    metrics: dict[str, Any] = Field(..., description="Updated metrics")
    updated_at: str = Field(..., description="Update timestamp")


class OrderUpdateMessage(BaseModel):
    """Order execution update message."""

    type: MessageType = Field(default=MessageType.ORDER_UPDATE, description="Message type")
    run_id: str = Field(..., description="Run ID")
    order: dict[str, Any] = Field(..., description="Order data")
    updated_at: str = Field(..., description="Update timestamp")


class ErrorMessage(BaseModel):
    """Error message."""

    type: MessageType = Field(default=MessageType.ERROR, description="Message type")
    error_code: str = Field(..., description="Error code")
    error_message: str = Field(..., description="Error description")
    run_id: str | None = Field(default=None, description="Related run ID")


class ConnectionStatusMessage(BaseModel):
    """Connection status message."""

    type: MessageType = Field(default=MessageType.CONNECTION_STATUS, description="Message type")
    status: ConnectionStatus = Field(..., description="Connection status")
    message: str | None = Field(default=None, description="Status message")
    backend_connected: bool = Field(..., description="Backend connection status")


class PingMessage(BaseModel):
    """Ping message for connection health check."""

    type: MessageType = Field(default=MessageType.PING, description="Message type")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="Ping timestamp"
    )


class PongMessage(BaseModel):
    """Pong response message."""

    type: MessageType = Field(default=MessageType.PONG, description="Message type")
    timestamp: str = Field(
        default_factory=lambda: datetime.utcnow().isoformat(), description="Pong timestamp"
    )
    ping_timestamp: str | None = Field(default=None, description="Original ping timestamp")


# Union type for all possible messages
WebSocketMessageUnion = (
    WebSocketMessage
    | SubscribeMessage
    | UnsubscribeMessage
    | RunUpdateMessage
    | MetricsUpdateMessage
    | OrderUpdateMessage
    | ErrorMessage
    | ConnectionStatusMessage
    | PingMessage
    | PongMessage
)
