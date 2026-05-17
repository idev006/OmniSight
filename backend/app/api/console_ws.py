"""
Pilot Console WebSocket — ADMIN only
- Receives all real-time events from Redis Pub/Sub
- Accepts control commands from admin browser
"""
import asyncio
import json
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query

from app.core.security import get_current_user_ws
from app.db.redis import redis
from app.services.camera_manager import camera_manager

logger = logging.getLogger(__name__)
router = APIRouter()


@router.websocket("/console")
async def console_ws(
    websocket: WebSocket,
    token: str = Query(default=""),
):
    # ── Auth — ADMIN only ────────────────────────────────────────────────────
    try:
        user = get_current_user_ws(token)
        if not user.is_admin:
            await websocket.close(code=4003, reason="Admin role required")
            return
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    await websocket.accept()
    logger.info(f"Pilot Console connected: user={user.username}")

    # ── Send initial state ───────────────────────────────────────────────────
    await websocket.send_text(json.dumps({
        "event": "init",
        "cameras": camera_manager.list_active(),
    }))

    # ── Subscribe to Redis Pub/Sub ───────────────────────────────────────────
    pubsub = redis.pubsub()
    await pubsub.subscribe("omnisight:events")

    async def relay_events():
        """Relay Redis pub/sub events → Console browser"""
        async for message in pubsub.listen():
            if message["type"] == "message":
                try:
                    await websocket.send_text(message["data"])
                except Exception:
                    break

    relay_task = asyncio.create_task(relay_events())

    # ── Command handler ──────────────────────────────────────────────────────
    try:
        while True:
            raw = await websocket.receive_text()
            try:
                cmd = json.loads(raw)
            except json.JSONDecodeError:
                continue

            action = cmd.get("action", "")
            camera_id = cmd.get("camera_id", "")

            if action == "pause_camera" and camera_id:
                ok = await camera_manager.pause(camera_id)
                await websocket.send_text(json.dumps({
                    "event": "ack",
                    "action": "pause_camera",
                    "camera_id": camera_id,
                    "ok": ok,
                }))

            elif action == "resume_camera" and camera_id:
                ok = await camera_manager.resume(camera_id)
                await websocket.send_text(json.dumps({
                    "event": "ack",
                    "action": "resume_camera",
                    "camera_id": camera_id,
                    "ok": ok,
                }))

            elif action == "disconnect_camera" and camera_id:
                await camera_manager.disconnect(camera_id, "Disconnected by admin")
                await websocket.send_text(json.dumps({
                    "event": "ack",
                    "action": "disconnect_camera",
                    "camera_id": camera_id,
                    "ok": True,
                }))

            elif action == "set_fps" and camera_id:
                fps = int(cmd.get("fps", 2))
                ok = await camera_manager.set_fps(camera_id, fps)
                await websocket.send_text(json.dumps({
                    "event": "ack",
                    "action": "set_fps",
                    "camera_id": camera_id,
                    "fps": fps,
                    "ok": ok,
                }))

            elif action == "list_cameras":
                await websocket.send_text(json.dumps({
                    "event": "cameras_list",
                    "cameras": camera_manager.list_active(),
                }))

    except WebSocketDisconnect:
        logger.info(f"Pilot Console disconnected: user={user.username}")
    except Exception as e:
        logger.error(f"Console WS error: {e}")
    finally:
        relay_task.cancel()
        try:
            await pubsub.unsubscribe("omnisight:events")
            await pubsub.close()
        except Exception:
            pass
