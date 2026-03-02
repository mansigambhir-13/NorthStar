"""WebSocket endpoint for streaming agent chat."""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/agent")
async def agent_chat(websocket: WebSocket) -> None:
    """WebSocket endpoint for streaming agent chat.

    Client sends: {"message": "..."}
    Server streams: {"type":"token","content":"..."} then {"type":"done"}
    """
    await websocket.accept()

    try:
        while True:
            data = await websocket.receive_json()
            message = data.get("message", "")
            if not message:
                await websocket.send_json({"type": "error", "content": "Empty message"})
                continue

            try:
                from northstar.agent.agent import NorthStarAgent

                async with NorthStarAgent() as agent:
                    response = await agent.chat(message)

                # Stream the response token-by-token
                chunk_size = 4
                for i in range(0, len(response), chunk_size):
                    chunk = response[i : i + chunk_size]
                    await websocket.send_json({"type": "token", "content": chunk})

                await websocket.send_json({"type": "done"})

            except Exception as e:
                logger.error("Agent chat error: %s", e)
                await websocket.send_json(
                    {"type": "error", "content": f"Agent error: {e}"}
                )

    except WebSocketDisconnect:
        logger.info("WebSocket client disconnected")
    except Exception as e:
        logger.error("WebSocket error: %s", e)
