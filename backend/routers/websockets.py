# backend/routers/websockets.py
import asyncio
import json
from typing import Dict, List, Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, HTTPException
from sqlalchemy.orm import Session
from backend.database import get_db
from backend.security import get_current_user_optional
from backend.schemas import WebSocketEvent, WebSocketEventPayload, ChamaSummary, ChamaAnalytics, Contribution
from backend.logging_config import setup_logging
from backend.models.user import User
from backend.models.membership import MembershipRole

logger = setup_logging()

# Global connection manager for WebSocket connections per Chama
class ConnectionManager:
    def __init__(self):
        self.active_connections: Dict[int, List[WebSocket]] = {}

    async def connect(self, websocket: WebSocket, chama_id: int):
        await websocket.accept()
        if chama_id not in self.active_connections:
            self.active_connections[chama_id] = []
        self.active_connections[chama_id].append(websocket)
        logger.info(f"WebSocket connection established for chama {chama_id}. Total connections: {len(self.active_connections[chama_id])}")

    def disconnect(self, websocket: WebSocket, chama_id: int):
        if chama_id in self.active_connections:
            try:
                self.active_connections[chama_id].remove(websocket)
                logger.info(f"WebSocket disconnected for chama {chama_id}. Remaining connections: {len(self.active_connections[chama_id])}")
                if not self.active_connections[chama_id]:
                    del self.active_connections[chama_id]
            except ValueError:
                pass  # WebSocket already removed

    async def broadcast(self, chama_id: int, message: dict):
        """Broadcast message to all connections for a specific chama"""
        if chama_id in self.active_connections:
            disconnected = []
            for connection in self.active_connections[chama_id]:
                try:
                    await connection.send_json(message)
                except Exception as e:
                    logger.warning(f"Failed to send WebSocket message: {str(e)}")
                    disconnected.append(connection)

            # Clean up disconnected connections
            for connection in disconnected:
                self.disconnect(connection, chama_id)

# Global connection manager instance
manager = ConnectionManager()

router = APIRouter(tags=["WebSockets"])

@router.websocket("/chamas/{chama_id}/updates")
async def chama_updates_websocket(
    websocket: WebSocket,
    chama_id: int,
    token: Optional[str] = None
):
    """
    WebSocket endpoint for real-time Chama updates.
    Clients must be authenticated members of the Chama.
    """
    try:
        # Authenticate user if token provided
        from backend.security import decode_access_token
        from backend.database import get_db
        from backend.models.membership import Membership

        membership = None

        if token:
            db = next(get_db())
            try:
                # Validate the token
                token_data = decode_access_token(token)

                # Check if user is a member of this chama
                membership = db.query(Membership).join(User).filter(
                    User.email == token_data.email,
                    Membership.chama_id == chama_id
                ).first()

                if not membership:
                    logger.warning(f"User {token_data.email} is not a member of chama {chama_id}")
                    await websocket.close(code=1008)  # Policy violation
                    return

            except Exception as e:
                logger.warning(f"WebSocket authentication failed: {str(e)}")
                await websocket.close(code=1008)  # Policy violation
                return
            finally:
                db.close()

        # Accept connection
        await manager.connect(websocket, chama_id)

        try:
            while True:
                # Keep connection alive and listen for client messages
                data = await websocket.receive_text()
                # For now, we only broadcast updates. Client messages could be used for acknowledgments
                if data == "ping":
                    await websocket.send_text("pong")

        except WebSocketDisconnect:
            manager.disconnect(websocket, chama_id)

    except Exception as e:
        logger.error(f"WebSocket error for chama {chama_id}: {str(e)}")
        manager.disconnect(websocket, chama_id)


# Utility functions for broadcasting events
async def broadcast_chama_update(chama_id: int, event_type: str, payload: dict):
    """
    Broadcast an event to all WebSocket connections for a chama.
    """
    from datetime import datetime, timezone

    event_data = {
        "event_type": event_type,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "payload": payload
    }

    await manager.broadcast(chama_id, event_data)
    logger.info(f"Broadcasted {event_type} event for chama {chama_id}")


async def broadcast_contribution_created(chama_id: int, contribution: Contribution, summary: Optional[ChamaSummary] = None, analytics: Optional[ChamaAnalytics] = None):
    """Broadcast contribution creation event"""
    payload = WebSocketEventPayload(
        summary=summary,
        analytics=analytics,
        contribution=contribution
    ).model_dump()

    await broadcast_chama_update(chama_id, "CONTRIBUTION_CREATED", payload)


async def broadcast_member_added(chama_id: int, summary: Optional[ChamaSummary] = None, analytics: Optional[ChamaAnalytics] = None):
    """Broadcast member addition event"""
    payload = WebSocketEventPayload(
        summary=summary,
        analytics=analytics
    ).model_dump()

    await broadcast_chama_update(chama_id, "MEMBER_ADDED", payload)


async def broadcast_chama_updated(chama_id: int, summary: Optional[ChamaSummary] = None, analytics: Optional[ChamaAnalytics] = None):
    """Broadcast chama update event"""
    payload = WebSocketEventPayload(
        summary=summary,
        analytics=analytics
    ).model_dump()

    await broadcast_chama_update(chama_id, "CHAMA_UPDATED", payload)


async def broadcast_analytics_updated(chama_id: int, summary: Optional[ChamaSummary] = None, analytics: Optional[ChamaAnalytics] = None):
    """Broadcast analytics update event"""
    payload = WebSocketEventPayload(
        summary=summary,
        analytics=analytics
    ).model_dump()

    await broadcast_chama_update(chama_id, "ANALYTICS_UPDATED", payload)
