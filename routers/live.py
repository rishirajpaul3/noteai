import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

import store
from services.live_coach import run_live_coaching

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/ws/calls/{bot_id}")
async def live_coaching_ws(websocket: WebSocket, bot_id: str):
    await websocket.accept()
    logger.info(f"[live_ws] client connected bot_id={bot_id}")

    call = store.get(bot_id)
    if not call:
        await websocket.send_json({"type": "error", "message": "Call not found"})
        await websocket.close()
        return

    if call.get("status") not in {"joining", "transcribing", "processing"}:
        await websocket.send_json({"type": "error", "message": "Call is not active"})
        await websocket.close()
        return

    async def send(data: dict):
        await websocket.send_json(data)

    # Send immediate acknowledgement so the frontend knows it's connected
    await websocket.send_json({"type": "connected", "message": "Live coaching active — tips will appear as the call progresses."})

    coaching_task = asyncio.create_task(run_live_coaching(bot_id, send))

    try:
        # Keep connection alive, handle client pings / disconnects
        while True:
            try:
                msg = await asyncio.wait_for(websocket.receive_text(), timeout=5.0)
                if msg == "ping":
                    await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                # Normal — just keep waiting
                if coaching_task.done():
                    break
    except WebSocketDisconnect:
        logger.info(f"[live_ws] client disconnected bot_id={bot_id}")
    finally:
        coaching_task.cancel()
        try:
            await coaching_task
        except asyncio.CancelledError:
            pass
        logger.info(f"[live_ws] session ended bot_id={bot_id}")
