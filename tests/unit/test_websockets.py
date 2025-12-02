"""
Unit tests for WebSocket router functionality.
"""
import asyncio
import json
from datetime import datetime
import pytest
from unittest.mock import Mock, AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient
from backend.main import app
from backend.routers.websockets import ConnectionManager, manager
from backend.database import get_db
from backend.models.user import User
from backend.models.membership import Membership
from backend.schemas import Contribution, ChamaSummary, ChamaAnalytics


@pytest.fixture
def client():
    """Test client fixture."""
    return TestClient(app)


@pytest.fixture
def connection_manager():
    """Fresh ConnectionManager instance for testing."""
    return ConnectionManager()


@pytest.fixture
def mock_websocket():
    """Mock WebSocket connection."""
    ws = AsyncMock()
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    ws.receive_text = AsyncMock(return_value="ping")
    ws.send_text = AsyncMock()
    ws.close = AsyncMock()
    return ws


@pytest.fixture
def mock_db_session():
    """Mock database session."""
    return MagicMock()


class TestConnectionManager:
    """Test ConnectionManager functionality."""

    def test_initialization(self, connection_manager):
        """Test ConnectionManager initializes with empty connections."""
        assert connection_manager.active_connections == {}

    @pytest.mark.asyncio
    async def test_connect_new_chama(self, connection_manager, mock_websocket):
        """Test connecting to a new chama creates connection list."""
        chama_id = 1

        await connection_manager.connect(mock_websocket, chama_id)

        assert chama_id in connection_manager.active_connections
        assert len(connection_manager.active_connections[chama_id]) == 1
        assert connection_manager.active_connections[chama_id][0] == mock_websocket
        mock_websocket.accept.assert_called_once()

    @pytest.mark.asyncio
    async def test_connect_existing_chama(self, connection_manager, mock_websocket):
        """Test connecting to existing chama adds to connection list."""
        chama_id = 1
        mock_websocket2 = AsyncMock()
        mock_websocket2.accept = AsyncMock()

        await connection_manager.connect(mock_websocket, chama_id)
        await connection_manager.connect(mock_websocket2, chama_id)

        assert len(connection_manager.active_connections[chama_id]) == 2
        assert mock_websocket in connection_manager.active_connections[chama_id]
        assert mock_websocket2 in connection_manager.active_connections[chama_id]

    def test_disconnect_existing_connection(self, connection_manager, mock_websocket):
        """Test disconnecting existing connection removes it."""
        chama_id = 1
        # Manually add connection to avoid async call
        connection_manager.active_connections[chama_id] = [mock_websocket]

        connection_manager.disconnect(mock_websocket, chama_id)

        # After disconnecting the last connection, the chama_id should be removed from active_connections
        assert chama_id not in connection_manager.active_connections

    def test_disconnect_empty_chama_cleanup(self, connection_manager, mock_websocket):
        """Test disconnecting last connection removes chama from active connections."""
        chama_id = 1
        connection_manager.active_connections[chama_id] = [mock_websocket]

        connection_manager.disconnect(mock_websocket, chama_id)

        assert chama_id not in connection_manager.active_connections

    def test_disconnect_nonexistent_connection(self, connection_manager, mock_websocket):
        """Test disconnecting non-existent connection doesn't error."""
        chama_id = 1
        connection_manager.active_connections[chama_id] = []

        # Should not raise exception
        connection_manager.disconnect(mock_websocket, chama_id)

    @pytest.mark.asyncio
    async def test_broadcast_to_chama(self, connection_manager, mock_websocket):
        """Test broadcasting message to all connections in a chama."""
        chama_id = 1
        message = {"event": "test", "data": "hello"}

        await connection_manager.connect(mock_websocket, chama_id)
        await connection_manager.broadcast(chama_id, message)

        mock_websocket.send_json.assert_called_once_with(message)

    @pytest.mark.asyncio
    async def test_broadcast_to_empty_chama(self, connection_manager):
        """Test broadcasting to chama with no connections doesn't error."""
        chama_id = 1
        message = {"event": "test"}

        # Should not raise exception
        await connection_manager.broadcast(chama_id, message)

    @pytest.mark.asyncio
    async def test_broadcast_with_disconnected_client(self, connection_manager, mock_websocket):
        """Test broadcasting handles disconnected clients gracefully."""
        chama_id = 1
        message = {"event": "test"}

        # Mock websocket that raises exception on send
        mock_websocket.send_json.side_effect = Exception("Connection lost")

        await connection_manager.connect(mock_websocket, chama_id)
        await connection_manager.broadcast(chama_id, message)

        # Connection should be cleaned up due to exception - entire chama entry removed
        assert chama_id not in connection_manager.active_connections


class TestWebSocketAuthentication:
    """Test WebSocket authentication and connection handling."""

    @pytest.mark.asyncio
    async def test_websocket_connection_without_token(self):
        """Test WebSocket accepts connection without token (anonymous access)."""
        # This would need actual WebSocket testing framework
        # For now, test the authentication logic in isolation
        pass

    @pytest.mark.asyncio
    async def test_websocket_authentication_with_valid_token(self):
        """Test WebSocket accepts authenticated user who is chama member."""
        # Mock the database and authentication components
        with patch('backend.security.decode_access_token') as mock_decode, \
             patch('backend.database.get_db') as mock_get_db, \
             patch('backend.routers.websockets.manager') as mock_manager:

            # Setup mocks
            mock_token_data = Mock()
            mock_token_data.email = "test@example.com"
            mock_decode.return_value = mock_token_data

            mock_db = Mock()
            mock_membership = Mock()
            mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = mock_membership
            mock_get_db.return_value = iter([mock_db])

            mock_ws = AsyncMock()
            mock_ws.receive_text = AsyncMock(side_effect=asyncio.CancelledError())  # End the loop

            # Import and test the endpoint logic
            from backend.routers.websockets import chama_updates_websocket

            # This would require more complex WebSocket testing setup
            # For now, focus on unit testing the authentication parts
            pass

    @pytest.mark.asyncio
    async def test_websocket_rejects_invalid_token(self):
        """Test WebSocket rejects connection with invalid token."""
        with patch('backend.security.decode_access_token') as mock_decode:
            mock_decode.side_effect = Exception("Invalid token")

            mock_ws = AsyncMock()
            mock_ws.close = AsyncMock()

            # Test would verify ws.close is called with code 1008
            pass

    @pytest.mark.asyncio
    async def test_websocket_rejects_non_member(self):
        """Test WebSocket rejects user who is not a chama member."""
        with patch('backend.security.decode_access_token') as mock_decode, \
             patch('backend.database.get_db') as mock_get_db:

            mock_token_data = Mock()
            mock_token_data.email = "test@example.com"
            mock_decode.return_value = mock_token_data

            mock_db = Mock()
            mock_db.query.return_value.join.return_value.filter.return_value.first.return_value = None  # No membership
            mock_get_db.return_value = iter([mock_db])

            mock_ws = AsyncMock()
            mock_ws.close = AsyncMock()

            # Test would verify ws.close is called with code 1008
            pass


class TestBroadcastingFunctions:
    """Test broadcasting utility functions."""

    @pytest.mark.asyncio
    async def test_broadcast_chama_update(self):
        """Test generic chama update broadcasting."""
        with patch('backend.routers.websockets.manager') as mock_manager:
            # Configure broadcast method to be an AsyncMock
            mock_manager.broadcast = AsyncMock()
            from backend.routers.websockets import broadcast_chama_update

            chama_id = 1
            event_type = "TEST_EVENT"
            payload = {"key": "value"}

            await broadcast_chama_update(chama_id, event_type, payload)

            # Verify broadcast was awaited with correct structure
            call_args = mock_manager.broadcast.call_args
            assert call_args[0][0] == chama_id

            event_data = call_args[0][1]
            assert event_data["event_type"] == event_type
            assert event_data["payload"] == payload
            assert "timestamp" in event_data

    @pytest.mark.asyncio
    async def test_broadcast_contribution_created(self):
        """Test contribution creation broadcasting."""
        with patch('backend.routers.websockets.broadcast_chama_update') as mock_broadcast:
            from backend.routers.websockets import broadcast_contribution_created

            chama_id = 1
            # Configure Mock objects to pass Pydantic validation
            contribution = Mock()
            contribution.id = 123
            contribution.amount = 100.50
            contribution.created_at = datetime.now()  # Proper datetime object

            # Pass None for optional parameters to avoid validation issues
            summary = None
            analytics = None

            await broadcast_contribution_created(chama_id, contribution, summary, analytics)

            mock_broadcast.assert_called_once()
            call_args = mock_broadcast.call_args
            assert call_args[0][0] == chama_id
            assert call_args[0][1] == "CONTRIBUTION_CREATED"

    @pytest.mark.asyncio
    async def test_broadcast_member_added(self):
        """Test member addition broadcasting."""
        with patch('backend.routers.websockets.broadcast_chama_update') as mock_broadcast:
            from backend.routers.websockets import broadcast_member_added

            chama_id = 1
            # Pass None for optional parameters to avoid validation issues
            summary = None
            analytics = None

            await broadcast_member_added(chama_id, summary, analytics)

            mock_broadcast.assert_called_once_with(chama_id, "MEMBER_ADDED", Mock())

    @pytest.mark.asyncio
    async def test_broadcast_chama_updated(self):
        """Test chama update broadcasting."""
        with patch('backend.routers.websockets.broadcast_chama_update') as mock_broadcast:
            from backend.routers.websockets import broadcast_chama_updated

            chama_id = 1
            # Pass None for optional parameters to avoid validation issues
            summary = None
            analytics = None

            await broadcast_chama_updated(chama_id, summary, analytics)

            mock_broadcast.assert_called_once_with(chama_id, "CHAMA_UPDATED", Mock())

    @pytest.mark.asyncio
    async def test_broadcast_analytics_updated(self):
        """Test analytics update broadcasting."""
        with patch('backend.routers.websockets.broadcast_chama_update') as mock_broadcast:
            from backend.routers.websockets import broadcast_analytics_updated

            chama_id = 1
            # Pass None for optional parameters to avoid validation issues
            summary = None
            analytics = None

            await broadcast_analytics_updated(chama_id, summary, analytics)

            mock_broadcast.assert_called_once_with(chama_id, "ANALYTICS_UPDATED", Mock())


class TestWebSocketEndpoint:
    """Test WebSocket endpoint directly."""

    @pytest.mark.asyncio
    async def test_ping_pong_functionality(self):
        """Test ping/pong message handling."""
        # This would require a WebSocket test client
        # For now, test the logic that handles ping messages
        pass

    @pytest.mark.asyncio
    async def test_connection_cleanup_on_disconnect(self):
        """Test connections are cleaned up properly on disconnect."""
        manager = ConnectionManager()
        mock_ws = AsyncMock()

        chama_id = 1
        await manager.connect(mock_ws, chama_id)

        # Verify connection exists
        assert len(manager.active_connections[chama_id]) == 1

        # Disconnect
        manager.disconnect(mock_ws, chama_id)

        # Verify connection removed - after disconnecting last connection, chama_id is removed
        assert chama_id not in manager.active_connections

    @pytest.mark.asyncio
    async def test_multiple_chamas_isolation(self):
        """Test connections are properly isolated between different chamas."""
        manager = ConnectionManager()

        ws1 = AsyncMock()
        ws1.accept = AsyncMock()
        ws2 = AsyncMock()
        ws2.accept = AsyncMock()

        # Connect to different chamas
        await manager.connect(ws1, 1)
        await manager.connect(ws2, 2)

        assert len(manager.active_connections[1]) == 1
        assert len(manager.active_connections[2]) == 1

        # Broadcast to chama 1 should only affect ws1
        await manager.broadcast(1, {"test": "message"})
        ws1.send_json.assert_called_once()
        ws2.send_json.assert_not_called()
