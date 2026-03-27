"""
WebSocket notifications — real-time push for alerts & announcements.
"""

import json
import asyncio
from typing import Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import decode_access_token
from app.database import get_db, async_session
from app.models.user import User, UserRole

router = APIRouter(tags=["WebSocket"])


class ConnectionManager:
    """Manages WebSocket connections per user."""

    def __init__(self):
        # user_id (str) → list of active WebSocket connections
        self.connections: Dict[str, List[WebSocket]] = {}

    async def connect(self, user_id: str, websocket: WebSocket):
        await websocket.accept()
        if user_id not in self.connections:
            self.connections[user_id] = []
        self.connections[user_id].append(websocket)

    def disconnect(self, user_id: str, websocket: WebSocket):
        if user_id in self.connections:
            self.connections[user_id] = [
                ws for ws in self.connections[user_id] if ws != websocket
            ]
            if not self.connections[user_id]:
                del self.connections[user_id]

    async def send_to_user(self, user_id: str, data: dict):
        """Send a message to all connections of a specific user."""
        if user_id in self.connections:
            dead = []
            for ws in self.connections[user_id]:
                try:
                    await ws.send_json(data)
                except Exception:
                    dead.append(ws)
            for ws in dead:
                self.connections[user_id].remove(ws)

    async def broadcast_to_users(self, user_ids: List[str], data: dict):
        """Send a message to multiple users."""
        for uid in user_ids:
            await self.send_to_user(uid, data)

    async def broadcast_to_roles(self, roles: List[UserRole], data: dict):
        """Send a message to all connected users with the given roles."""
        # Get user IDs for the target roles from connected users
        async with async_session() as db:
            connected_ids = list(self.connections.keys())
            if not connected_ids:
                return
            result = await db.execute(
                select(User.id).where(
                    User.id.in_(connected_ids),
                    User.role.in_(roles),
                )
            )
            target_ids = [str(row[0]) for row in result.all()]
        await self.broadcast_to_users(target_ids, data)

    async def broadcast_all(self, data: dict):
        """Send to all connected users."""
        for uid in list(self.connections.keys()):
            await self.send_to_user(uid, data)


# Global singleton
manager = ConnectionManager()


@router.websocket("/ws/notifications")
async def websocket_notifications(websocket: WebSocket):
    """
    WebSocket endpoint for real-time notifications.
    Auth via query param: /ws/notifications?token=<jwt>
    """
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=4001, reason="Missing token")
        return

    payload = decode_access_token(token)
    if not payload:
        await websocket.close(code=4001, reason="Invalid token")
        return

    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=4001, reason="Invalid token payload")
        return

    await manager.connect(user_id, websocket)
    try:
        # Keep connection alive — just listen for pings/client messages
        while True:
            try:
                data = await asyncio.wait_for(websocket.receive_text(), timeout=30)
                # Client can send "ping" to keep alive
                if data == "ping":
                    await websocket.send_text("pong")
            except asyncio.TimeoutError:
                # Send a ping to check if connection is alive
                try:
                    await websocket.send_text("ping")
                except Exception:
                    break
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        manager.disconnect(user_id, websocket)
