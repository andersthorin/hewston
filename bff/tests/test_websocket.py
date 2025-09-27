"""
WebSocket Tests

Tests for the WebSocket functionality following the acceptance criteria
from Story 8.5 and the QA checklist.
"""

import pytest
import json
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import WebSocket


class TestWebSocketConnectionManager:
    """Test suite for WebSocket connection management."""
    
    @pytest.mark.asyncio
    async def test_client_connection_lifecycle(self):
        """Test client connection and disconnection."""
        from bff.services.websocket_manager import WebSocketConnectionManager
        
        # Arrange
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "test-connection-123"
        
        # Act - Connect
        await manager.connect_client(mock_websocket, connection_id)
        
        # Assert - Connection established
        assert connection_id in manager.active_connections
        assert connection_id in manager.connection_metadata
        assert manager.connection_metadata[connection_id]["subscriptions"] == set()
        mock_websocket.accept.assert_called_once()
        
        # Act - Disconnect
        await manager.disconnect_client(connection_id)
        
        # Assert - Connection cleaned up
        assert connection_id not in manager.active_connections
        assert connection_id not in manager.connection_metadata
    
    @pytest.mark.asyncio
    async def test_subscription_management(self):
        """Test run subscription and unsubscription."""
        from bff.services.websocket_manager import WebSocketConnectionManager
        
        # Arrange
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "test-connection-123"
        run_id = "test-run-456"
        
        await manager.connect_client(mock_websocket, connection_id)
        
        # Mock backend connection to avoid actual WebSocket connection
        with patch.object(manager, '_ensure_backend_connection', new_callable=AsyncMock):
            # Act - Subscribe
            subscribe_message = {
                "type": "subscribe",
                "run_id": run_id,
                "updates": ["run_status", "metrics"]
            }
            await manager.handle_client_message(connection_id, json.dumps(subscribe_message))
            
            # Assert - Subscription added
            assert run_id in manager.run_subscriptions
            assert connection_id in manager.run_subscriptions[run_id]
            assert run_id in manager.connection_metadata[connection_id]["subscriptions"]
            
            # Act - Unsubscribe
            unsubscribe_message = {
                "type": "unsubscribe",
                "run_id": run_id
            }
            await manager.handle_client_message(connection_id, json.dumps(unsubscribe_message))
            
            # Assert - Subscription removed
            assert run_id not in manager.run_subscriptions or connection_id not in manager.run_subscriptions[run_id]
            assert run_id not in manager.connection_metadata[connection_id]["subscriptions"]
    
    @pytest.mark.asyncio
    async def test_ping_pong_handling(self):
        """Test ping/pong message handling."""
        from bff.services.websocket_manager import WebSocketConnectionManager
        
        # Arrange
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "test-connection-123"
        
        await manager.connect_client(mock_websocket, connection_id)
        
        # Act - Send ping
        ping_message = {
            "type": "ping",
            "timestamp": "2024-01-01T00:00:00Z"
        }
        await manager.handle_client_message(connection_id, json.dumps(ping_message))
        
        # Assert - Pong sent
        mock_websocket.send_text.assert_called()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "pong"
        assert sent_message["ping_timestamp"] == "2024-01-01T00:00:00Z"
    
    @pytest.mark.asyncio
    async def test_invalid_message_handling(self):
        """Test handling of invalid messages."""
        from bff.services.websocket_manager import WebSocketConnectionManager
        
        # Arrange
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "test-connection-123"
        
        await manager.connect_client(mock_websocket, connection_id)
        
        # Act - Send invalid JSON
        await manager.handle_client_message(connection_id, "invalid json")
        
        # Assert - Error message sent
        mock_websocket.send_text.assert_called()
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "error"
        assert sent_message["error_code"] == "INVALID_JSON"
        
        # Act - Send unknown message type
        unknown_message = {"type": "unknown_type"}
        await manager.handle_client_message(connection_id, json.dumps(unknown_message))
        
        # Assert - Error message sent
        sent_message = json.loads(mock_websocket.send_text.call_args[0][0])
        assert sent_message["type"] == "error"
        assert sent_message["error_code"] == "UNKNOWN_MESSAGE_TYPE"
    
    def test_connection_stats(self):
        """Test connection statistics."""
        from bff.services.websocket_manager import WebSocketConnectionManager
        
        # Arrange
        manager = WebSocketConnectionManager()
        
        # Add mock connections and subscriptions
        manager.active_connections["conn1"] = MagicMock()
        manager.active_connections["conn2"] = MagicMock()
        manager.run_subscriptions["run1"] = {"conn1", "conn2"}
        manager.run_subscriptions["run2"] = {"conn1"}
        manager.backend_connections["run1"] = MagicMock()
        
        # Act
        stats = manager.get_connection_stats()
        
        # Assert
        assert stats["active_connections"] == 2
        assert stats["run_subscriptions"] == 2
        assert stats["backend_connections"] == 1
        assert stats["total_subscribers"] == 3  # conn1 + conn2 + conn1


class TestWebSocketAPI:
    """Test suite for WebSocket API endpoints."""
    
    def test_websocket_stats_endpoint(self, test_client: TestClient):
        """Test WebSocket statistics endpoint."""
        # Act
        response = test_client.get("/api/v1/websocket/stats")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert "websocket_stats" in data
        assert "active_connections" in data["websocket_stats"]
        assert "run_subscriptions" in data["websocket_stats"]
        assert "backend_connections" in data["websocket_stats"]
        assert "total_subscribers" in data["websocket_stats"]
    
    def test_websocket_health_endpoint(self, test_client: TestClient):
        """Test WebSocket health check endpoint."""
        # Act
        response = test_client.get("/api/v1/websocket/health")
        
        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "websocket"
        assert "active_connections" in data
        assert "backend_connections" in data


class TestWebSocketModels:
    """Test suite for WebSocket message models."""
    
    def test_subscribe_message_validation(self):
        """Test subscribe message model validation."""
        from bff.models.websocket import SubscribeMessage, MessageType
        
        # Valid message
        message = SubscribeMessage(
            run_id="test-run-123",
            updates=["run_status", "metrics"]
        )
        assert message.type == MessageType.SUBSCRIBE
        assert message.run_id == "test-run-123"
        assert message.updates == ["run_status", "metrics"]
        
        # Default updates
        message_default = SubscribeMessage(run_id="test-run-123")
        assert message_default.updates == ["run_status", "metrics", "orders"]
    
    def test_error_message_creation(self):
        """Test error message model."""
        from bff.models.websocket import ErrorMessage, MessageType
        
        # Create error message
        error = ErrorMessage(
            error_code="TEST_ERROR",
            error_message="Test error message",
            run_id="test-run-123"
        )
        
        assert error.type == MessageType.ERROR
        assert error.error_code == "TEST_ERROR"
        assert error.error_message == "Test error message"
        assert error.run_id == "test-run-123"
    
    def test_connection_status_message(self):
        """Test connection status message model."""
        from bff.models.websocket import ConnectionStatusMessage, ConnectionStatus, MessageType
        
        # Create status message
        status = ConnectionStatusMessage(
            status=ConnectionStatus.CONNECTED,
            message="Connected successfully",
            backend_connected=True
        )
        
        assert status.type == MessageType.CONNECTION_STATUS
        assert status.status == ConnectionStatus.CONNECTED
        assert status.message == "Connected successfully"
        assert status.backend_connected is True
    
    def test_run_update_message(self):
        """Test run update message model."""
        from bff.models.websocket import RunUpdateMessage, MessageType
        
        # Create run update
        update = RunUpdateMessage(
            run_id="test-run-123",
            status="RUNNING",
            progress=45.5,
            message="Processing data",
            updated_at="2024-01-01T00:00:00Z"
        )
        
        assert update.type == MessageType.RUN_UPDATE
        assert update.run_id == "test-run-123"
        assert update.status == "RUNNING"
        assert update.progress == 45.5
        assert update.message == "Processing data"


class TestWebSocketIntegration:
    """Test suite for WebSocket integration scenarios."""
    
    @pytest.mark.asyncio
    async def test_multiple_client_subscription(self):
        """Test multiple clients subscribing to same run."""
        from bff.services.websocket_manager import WebSocketConnectionManager
        
        # Arrange
        manager = WebSocketConnectionManager()
        mock_ws1 = AsyncMock()
        mock_ws2 = AsyncMock()
        conn1_id = "conn1"
        conn2_id = "conn2"
        run_id = "test-run-123"
        
        await manager.connect_client(mock_ws1, conn1_id)
        await manager.connect_client(mock_ws2, conn2_id)
        
        # Mock backend connection
        with patch.object(manager, '_ensure_backend_connection', new_callable=AsyncMock):
            # Act - Both clients subscribe to same run
            subscribe_msg = {"type": "subscribe", "run_id": run_id}
            await manager.handle_client_message(conn1_id, json.dumps(subscribe_msg))
            await manager.handle_client_message(conn2_id, json.dumps(subscribe_msg))
            
            # Assert - Both clients subscribed
            assert run_id in manager.run_subscriptions
            assert conn1_id in manager.run_subscriptions[run_id]
            assert conn2_id in manager.run_subscriptions[run_id]
            assert len(manager.run_subscriptions[run_id]) == 2
    
    @pytest.mark.asyncio
    async def test_client_disconnect_cleanup(self):
        """Test cleanup when client disconnects with active subscriptions."""
        from bff.services.websocket_manager import WebSocketConnectionManager
        
        # Arrange
        manager = WebSocketConnectionManager()
        mock_websocket = AsyncMock()
        connection_id = "test-connection-123"
        run_id = "test-run-456"
        
        await manager.connect_client(mock_websocket, connection_id)
        
        # Mock backend connection
        with patch.object(manager, '_ensure_backend_connection', new_callable=AsyncMock):
            # Subscribe to run
            subscribe_msg = {"type": "subscribe", "run_id": run_id}
            await manager.handle_client_message(connection_id, json.dumps(subscribe_msg))
            
            # Verify subscription exists
            assert run_id in manager.run_subscriptions
            assert connection_id in manager.run_subscriptions[run_id]
            
            # Act - Disconnect client
            await manager.disconnect_client(connection_id)
            
            # Assert - Subscriptions cleaned up
            assert connection_id not in manager.active_connections
            assert run_id not in manager.run_subscriptions or len(manager.run_subscriptions[run_id]) == 0
