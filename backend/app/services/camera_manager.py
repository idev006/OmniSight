"""
CameraManager — Single Source of Truth for camera connection state
- Register/deregister cameras (hot plug)
- Track FPS, last frame, status per camera
- Relay commands: pause / resume / disconnect
- Publish events → Redis Pub/Sub → Pilot Console
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field

from app.db.redis import redis

logger = logging.getLogger(__name__)


@dataclass
class CameraConnection:
    camera_id: str
    station_id: str
    camera_type: str  # WEBCAM | IP_CAMERA | CCTV | SMARTPHONE
    websocket: object  # FastAPI WebSocket
    connected_at: float = field(default_factory=time.monotonic)
    last_frame: float = field(default_factory=time.monotonic)
    frame_count: int = 0
    fps: float = 0.0
    status: str = "active"  # active | paused | offline


class CameraManager:
    """
    Singleton. ทุก WebSocket handler ใช้ instance เดียวกัน.
    State ใน-process: self._connections
    State cross-process: Redis keys
    """

    def __init__(self):
        self._connections: dict[str, CameraConnection] = {}
        self._lock = asyncio.Lock()

    # ─── Register / Deregister ────────────────────────────────────────────────

    async def register(self, camera_id: str, station_id: str, camera_type: str, websocket) -> CameraConnection:
        async with self._lock:
            # C-001: Duplicate camera_id — kick old connection (last-writer-wins)
            old = self._connections.get(camera_id)
            if old:
                try:
                    await old.websocket.close(code=4409, reason="Replaced by new connection")
                except Exception:
                    pass
                logger.info(f"Camera {camera_id}: old connection replaced")

            conn = CameraConnection(
                camera_id=camera_id, station_id=station_id, camera_type=camera_type, websocket=websocket
            )
            self._connections[camera_id] = conn

        # Persist to Redis
        await self._redis_set_status(camera_id, "active")
        try:
            await redis.sadd(f"station:{station_id}:cameras", camera_id)
            await redis.sadd("cameras:active", camera_id)
        except Exception:
            pass

        await self._publish(
            {
                "event": "camera_connected",
                "camera_id": camera_id,
                "station_id": station_id,
                "camera_type": camera_type,
            }
        )
        logger.info(f"Camera registered: {camera_id} @ station={station_id}")
        return conn

    async def deregister(self, camera_id: str):
        async with self._lock:
            conn = self._connections.pop(camera_id, None)

        if conn:
            await self._redis_set_status(camera_id, "offline")
            try:
                await redis.srem(f"station:{conn.station_id}:cameras", camera_id)
                await redis.srem("cameras:active", camera_id)
            except Exception:
                pass
            await self._publish(
                {
                    "event": "camera_disconnected",
                    "camera_id": camera_id,
                    "station_id": conn.station_id,
                    "frame_count": conn.frame_count,
                }
            )
            logger.info(f"Camera deregistered: {camera_id}")

    # ─── Commands ─────────────────────────────────────────────────────────────

    async def pause(self, camera_id: str) -> bool:
        conn = self._connections.get(camera_id)
        if not conn:
            return False
        try:
            await conn.websocket.send_text(json.dumps({"action": "pause"}))
            conn.status = "paused"
            await self._redis_set_status(camera_id, "paused")
            await self._publish({"event": "camera_paused", "camera_id": camera_id})
            return True
        except Exception as e:
            logger.error(f"Pause failed for {camera_id}: {e}")
            return False

    async def resume(self, camera_id: str) -> bool:
        conn = self._connections.get(camera_id)
        if not conn:
            return False
        try:
            await conn.websocket.send_text(json.dumps({"action": "resume"}))
            conn.status = "active"
            await self._redis_set_status(camera_id, "active")
            await self._publish({"event": "camera_resumed", "camera_id": camera_id})
            return True
        except Exception as e:
            logger.error(f"Resume failed for {camera_id}: {e}")
            return False

    async def disconnect(self, camera_id: str, reason: str = "Disconnected by server"):
        conn = self._connections.get(camera_id)
        if conn:
            try:
                await conn.websocket.send_text(json.dumps({"action": "disconnect", "reason": reason}))
                await conn.websocket.close(code=4000, reason=reason)
            except Exception:
                pass
            await self.deregister(camera_id)

    async def set_fps(self, camera_id: str, fps: int) -> bool:
        conn = self._connections.get(camera_id)
        if not conn:
            return False
        try:
            await conn.websocket.send_text(json.dumps({"action": "set_fps", "fps": fps}))
            return True
        except Exception:
            return False

    # ─── Frame Recording ──────────────────────────────────────────────────────

    def record_frame(self, camera_id: str):
        """Call on every received frame — updates FPS counter."""
        conn = self._connections.get(camera_id)
        if not conn:
            return
        now = time.monotonic()
        elapsed = now - conn.last_frame
        if elapsed > 0:
            instant_fps = 1.0 / elapsed
            conn.fps = 0.8 * conn.fps + 0.2 * instant_fps  # EMA
        conn.last_frame = now
        conn.frame_count += 1

        # Update Redis last_seen (non-blocking fire-and-forget)
        asyncio.ensure_future(self._update_last_seen(camera_id, now))

    # ─── Status Queries ───────────────────────────────────────────────────────

    def get_status(self, camera_id: str) -> dict:
        conn = self._connections.get(camera_id)
        if not conn:
            return {"status": "offline", "fps": 0.0, "frame_count": 0}
        return {
            "status": conn.status,
            "fps": round(conn.fps, 2),
            "frame_count": conn.frame_count,
            "connected_at": conn.connected_at,
        }

    def list_active(self) -> list[dict]:
        return [
            {
                "camera_id": c.camera_id,
                "station_id": c.station_id,
                "camera_type": c.camera_type,
                "status": c.status,
                "fps": round(c.fps, 2),
                "frame_count": c.frame_count,
            }
            for c in self._connections.values()
        ]

    # ─── Pilot Console Broadcasting ───────────────────────────────────────────

    async def broadcast_attendance(
        self, camera_id: str, station_id: str, employee_id: str, full_name: str, confidence: float, logged: bool
    ):
        event_name = "attendance_logged" if logged else "attendance_cooldown"
        await self._publish(
            {
                "event": event_name,
                "camera_id": camera_id,
                "station_id": station_id,
                "employee_id": employee_id,
                "full_name": full_name,
                "confidence": round(confidence, 4),
            }
        )

    async def broadcast_unknown(self, camera_id: str, station_id: str, bbox: dict):
        await self._publish(
            {
                "event": "unknown_face",
                "camera_id": camera_id,
                "station_id": station_id,
                "bbox": bbox,
            }
        )

    # ─── Heartbeat Monitor ────────────────────────────────────────────────────

    async def heartbeat_monitor(self, timeout_seconds: float = 30.0):
        """Background task — detects stale cameras (no frames > timeout)"""
        while True:
            await asyncio.sleep(10)
            now = time.monotonic()
            for cam_id, conn in list(self._connections.items()):
                if conn.status == "paused":
                    continue
                idle = now - conn.last_frame
                if idle > timeout_seconds:
                    logger.warning(f"Camera {cam_id} idle {idle:.0f}s → marking offline")
                    conn.status = "offline"
                    await self._redis_set_status(cam_id, "offline")
                    await self._publish(
                        {
                            "event": "camera_offline",
                            "camera_id": cam_id,
                            "idle_seconds": round(idle),
                        }
                    )

    # ─── Internal Helpers ─────────────────────────────────────────────────────

    async def _redis_set_status(self, camera_id: str, status: str):
        try:
            await redis.set(f"camera:{camera_id}:status", status, ex=3600)
        except Exception:
            pass

    async def _update_last_seen(self, camera_id: str, ts: float):
        try:
            await redis.set(f"camera:{camera_id}:last_seen", str(ts), ex=60)
        except Exception:
            pass

    async def _publish(self, event: dict):
        try:
            await redis.publish("omnisight:events", json.dumps(event))
        except Exception as e:
            logger.debug(f"Event publish failed: {e}")


# Singleton — import ตรงนี้จากทุกที่
camera_manager = CameraManager()
