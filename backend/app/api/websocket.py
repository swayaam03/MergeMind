"""WebSocket manager for streaming real-time pipeline and merge resolution progress."""

import asyncio
import json
import logging
from typing import Any, Dict, List
from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["websocket"])


class ConnectionManager:
    """Manages active WebSocket client connections grouped by channel."""

    def __init__(self) -> None:
        self.active_connections: Dict[str, List[WebSocket]] = {}
        self._lock = asyncio.Lock()

    async def connect(self, websocket: WebSocket, channel_id: str) -> None:
        """Accept connection and register websocket client under the channel."""
        await websocket.accept()
        async with self._lock:
            if channel_id not in self.active_connections:
                self.active_connections[channel_id] = []
            self.active_connections[channel_id].append(websocket)
        logger.info("WebSocket client connected to channel: %s", channel_id)

    async def disconnect(self, websocket: WebSocket, channel_id: str) -> None:
        """Unregister websocket client upon disconnection."""
        async with self._lock:
            if channel_id in self.active_connections:
                if websocket in self.active_connections[channel_id]:
                    self.active_connections[channel_id].remove(websocket)
                if not self.active_connections[channel_id]:
                    del self.active_connections[channel_id]
        logger.info("WebSocket client disconnected from channel: %s", channel_id)

    async def broadcast(self, channel_id: str, message: Dict[str, Any]) -> None:
        """Broadcast a JSON message to all subscribers of the specified channel."""
        async with self._lock:
            subscribers = list(self.active_connections.get(channel_id, []))

        if not subscribers:
            return

        payload = json.dumps(message)
        dead_connections: List[WebSocket] = []

        for ws in subscribers:
            try:
                await ws.send_text(payload)
            except Exception as exc:
                logger.warning("Failed to deliver WebSocket message to client on %s: %s", channel_id, exc)
                dead_connections.append(ws)

        if dead_connections:
            async with self._lock:
                for dead_ws in dead_connections:
                    if channel_id in self.active_connections and dead_ws in self.active_connections[channel_id]:
                        self.active_connections[channel_id].remove(dead_ws)


ws_manager = ConnectionManager()


async def broadcast_pipeline_event(
    channel_id: str,
    stage: str,
    status: str,
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Helper to emit structured progress events to connected UI clients."""
    await ws_manager.broadcast(
        channel_id=channel_id,
        message={
            "stage": stage,
            "status": status,
            "details": details or {},
        },
    )


@router.websocket("/ws/progress/{channel_id}")
async def websocket_pipeline_progress(websocket: WebSocket, channel_id: str) -> None:
    """
    WebSocket endpoint for real-time progress updates.
    Channel ID format typically: `{owner}_{repo}_{pull_number}` or `{run_id}`.
    """
    await ws_manager.connect(websocket, channel_id)
    try:
        # Send initial connected handshake
        await websocket.send_json(
            {
                "type": "connection_established",
                "channel": channel_id,
                "message": "Connected to MergeMind live pipeline feed.",
            }
        )
        while True:
            # Keep connection alive; clients can send ping messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text("pong")
    except WebSocketDisconnect:
        await ws_manager.disconnect(websocket, channel_id)
    except Exception as exc:
        logger.error("WebSocket unexpected error on channel %s: %s", channel_id, exc)
        await ws_manager.disconnect(websocket, channel_id)
