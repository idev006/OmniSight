"""
WebSocket Scan Handler — Multi-Camera Edition
ws/scan/{station_id}?token={jwt}&camera_id={id}

Design for plug-and-play multi-camera:
  1. FPS gate per camera   — backend-side rate limiter, prevents CPU overload
                             regardless of how fast the camera sends frames
  2. Thread pool executor  — face_engine.get_detections() is CPU-bound ONNX;
                             running it in executor keeps event loop free so
                             all camera connections receive frames concurrently
  3. Redis-cached FPS cap  — admin changes max_fps_per_camera in Settings UI,
                             write-through to Redis, websocket reads it live
  4. Last-writer-wins      — CameraManager handles duplicate camera_id by
                             closing the old connection gracefully
"""
import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Optional

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from qdrant_client.models import Filter, FieldCondition, MatchAny

from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import get_current_user_ws
from app.core.face_engine import face_engine, anti_spoof_engine
from app.db.postgres import async_session_factory
from app.db.qdrant import get_qdrant_sync
from app.db.redis import (
    get_station_filter, redis as _redis,
    increment_unknown_count, get_unknown_alert_threshold,
    get_anti_spoof_enabled, get_anti_spoof_threshold,
)
from app.models.orm import Employee, Department
from app.models.schemas import BBox, FaceResult, ScanResult
from app.services.attendance_service import log_attendance
from app.services.camera_manager import camera_manager
from datetime import datetime, timezone

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# ── Thread pool for CPU-bound face inference ──────────────────────────────────
# All cameras share this pool. Workers = inference_workers setting (default 2).
# With 2 workers: 2 cameras process concurrently, others queue.
# Prevents: face engine blocking the event loop and starving other cameras.
_executor = ThreadPoolExecutor(
    max_workers=settings.inference_workers,
    thread_name_prefix="face-worker",
)

# ── Per-camera FPS tracking (module-level, lives for process lifetime) ─────────
# _last_processed[camera_id] = monotonic timestamp of last processed frame
# Frames arriving faster than 1/max_fps are discarded (not queued) to prevent
# memory buildup when a fast source (e.g. 30 FPS webcam) feeds a slow backend.
_last_processed: dict[str, float] = {}


async def _get_max_fps() -> float:
    """
    Read max_fps_per_camera from Redis (write-through cache from settings.py).
    Falls back to config default if Redis unavailable.
    This allows admin to change FPS cap without restarting the backend.
    """
    try:
        val = await _redis.get("setting:max_fps_per_camera")
        if val:
            return max(0.1, float(val))
    except Exception:
        pass
    return float(settings.max_fps_per_camera)


async def _get_match_threshold() -> float:
    try:
        val = await _redis.get("setting:match_threshold")
        if val:
            return max(0.1, min(1.0, float(val)))
    except Exception:
        pass
    return float(settings.match_threshold)


@router.websocket("/scan/{station_id}")
async def scan_ws(
    websocket: WebSocket,
    station_id: str,
    token: str = Query(default=""),
    camera_id: str = Query(default=""),
):
    # ── Auth ────────────────────────────────────────────────────────────────
    try:
        user = get_current_user_ws(token)
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    # ── Station authorization ────────────────────────────────────────────────
    if not user.can_access_station(station_id):
        await websocket.close(code=4003, reason="No access to this station")
        return

    # ── camera_id assignment ─────────────────────────────────────────────────
    # If client doesn't provide camera_id, auto-generate one.
    # Convention: {type_prefix}-{user_id[:6]}-{station_id[:6]}
    # This gives a unique-enough ID for the session and makes logs readable.
    if not camera_id:
        type_prefix = "sm" if user.role == "OPERATOR" else "wc"
        camera_id = f"{type_prefix}-{user.user_id[:6]}-{station_id[:6]}"

    camera_type = "SMARTPHONE" if user.role == "OPERATOR" else "WEBCAM"

    await websocket.accept()
    logger.info(f"WS connected: camera={camera_id} station={station_id} user={user.username}")

    # ── Register camera (hot plug — displaces any existing same camera_id) ──
    await camera_manager.register(
        camera_id=camera_id,
        station_id=station_id,
        camera_type=camera_type,
        websocket=websocket,
    )

    # ── Read live FPS cap from Redis ──────────────────────────────────────────
    max_fps = await _get_max_fps()
    min_interval = 1.0 / max_fps   # minimum seconds between processed frames
    logger.info(f"Camera {camera_id}: max_fps={max_fps:.1f} min_interval={min_interval:.3f}s")

    qdrant = get_qdrant_sync()
    paused = False
    loop   = asyncio.get_event_loop()

    try:
        async with async_session_factory() as db:
            while True:
                # ── Receive frame ─────────────────────────────────────────
                raw = await websocket.receive_bytes()

                # FPS tracker (counts every received frame, not just processed)
                camera_manager.record_frame(camera_id)

                # ── Handle control messages from server (pause/resume/set_fps) ─
                # (sent as JSON text, but receive_bytes is used for frames;
                #  control messages arrive via the Pilot Console → camera_manager
                #  → websocket.send_text(), not as incoming bytes here.
                #  Pause state is toggled by CameraManager.)
                conn = camera_manager._connections.get(camera_id)
                if conn and conn.status == "paused":
                    paused = True
                elif conn and conn.status == "active":
                    paused = False

                if paused:
                    # Still receive frames (keep connection alive) but don't process
                    continue

                # ── FPS gate ─────────────────────────────────────────────────
                # Drop frames that arrive faster than max_fps.
                # This is critical: a 30 FPS webcam would otherwise saturate the
                # face engine. We drop silently — no error, no queue buildup.
                now = time.monotonic()
                elapsed = now - _last_processed.get(camera_id, 0.0)
                if elapsed < min_interval:
                    continue  # skip — too soon since last processed frame
                _last_processed[camera_id] = now

                # ── Decode JPEG → numpy ───────────────────────────────────────
                arr = np.frombuffer(raw, np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                # ── Face detection (CPU-bound → thread pool) ──────────────────
                # run_in_executor keeps the event loop free so OTHER camera
                # connections can receive their frames while this one is detecting.
                detections = await loop.run_in_executor(
                    _executor, face_engine.get_detections, frame
                )

                if not detections:
                    await websocket.send_text(
                        ScanResult(
                            timestamp=datetime.now(timezone.utc),
                            camera_id=camera_id,
                            faces=[],
                        ).model_dump_json()
                    )
                    continue

                # ── Station dept filter (Redis < 1ms) ─────────────────────────
                dept_ids = await get_station_filter(station_id)
                qdrant_filter = None
                if dept_ids:
                    qdrant_filter = Filter(
                        must=[FieldCondition(
                            key="dept_id",
                            match=MatchAny(any=dept_ids),
                        )]
                    )

                faces: list[FaceResult] = []
                match_threshold   = await _get_match_threshold()
                spoof_enabled     = await get_anti_spoof_enabled() and anti_spoof_engine.available
                spoof_threshold   = await get_anti_spoof_threshold() if spoof_enabled else 0.6

                for tracking_id, embedding, bbox in detections:
                    # Anti-spoofing gate — reject photo/video replay attacks
                    if spoof_enabled:
                        is_live, spoof_score = await loop.run_in_executor(
                            _executor,
                            lambda b=bbox: anti_spoof_engine.check_liveness(frame, b, spoof_threshold),
                        )
                        if not is_live:
                            faces.append(FaceResult(
                                tracking_id=tracking_id,
                                status="spoof",
                                confidence=spoof_score,
                                bbox=BBox(x=bbox[0], y=bbox[1],
                                          w=bbox[2]-bbox[0], h=bbox[3]-bbox[1]),
                                attendance_logged=False,
                            ))
                            continue
                    # Qdrant search — synchronous client → thread pool
                    results = await loop.run_in_executor(
                        _executor,
                        partial(
                            qdrant.search,
                            collection_name=settings.qdrant_collection,
                            query_vector=embedding.tolist(),
                            query_filter=qdrant_filter,
                            limit=1,
                            score_threshold=match_threshold,
                        )
                    )

                    if results:
                        hit         = results[0]
                        employee_id = hit.payload.get("employee_id")
                        confidence  = hit.score

                        # Fetch employee details from DB (full_name, emp_code, dept_name)
                        # These are NOT stored in Qdrant payload — only employee_id & dept_id are.
                        full_name = ""
                        emp_code  = None
                        dept_name = None
                        try:
                            emp_row = await db.execute(
                                select(Employee, Department.name.label("dept_name"))
                                .join(Department, Department.id == Employee.dept_id, isouter=True)
                                .where(Employee.id == employee_id)
                            )
                            emp_row = emp_row.first()
                            if emp_row:
                                emp_obj   = emp_row[0]
                                full_name = emp_obj.full_name or ""
                                emp_code  = emp_obj.emp_code
                                dept_name = emp_row[1]  # dept_name label
                        except Exception as e:
                            logger.warning(f"Employee lookup failed: {e}")

                        # Crop face for snapshot evidence (with 25% padding)
                        face_crop_jpg: Optional[bytes] = None
                        try:
                            x1, y1, x2, y2 = bbox
                            ih, iw = frame.shape[:2]
                            pad_x = int((x2 - x1) * 0.25)
                            pad_y = int((y2 - y1) * 0.25)
                            cx1 = max(0, x1 - pad_x)
                            cy1 = max(0, y1 - pad_y)
                            cx2 = min(iw, x2 + pad_x)
                            cy2 = min(ih, y2 + pad_y)
                            crop = frame[cy1:cy2, cx1:cx2]
                            if crop.size > 0:
                                ok, buf = cv2.imencode(
                                    '.jpg', crop,
                                    [cv2.IMWRITE_JPEG_QUALITY, 85]
                                )
                                if ok:
                                    face_crop_jpg = buf.tobytes()
                        except Exception as _crop_err:
                            logger.warning(f"Face crop failed: {_crop_err}")

                        log_id = await log_attendance(
                            db=db,
                            employee_id=employee_id,
                            station_id=station_id,
                            confidence_score=confidence,
                            face_crop_jpg=face_crop_jpg,
                        )
                        logged = log_id is not None

                        await camera_manager.broadcast_attendance(
                            camera_id=camera_id,
                            station_id=station_id,
                            employee_id=employee_id,
                            full_name=full_name,
                            confidence=confidence,
                            logged=logged,
                        )

                        faces.append(FaceResult(
                            tracking_id=tracking_id,
                            status="match",
                            employee_id=employee_id,
                            full_name=full_name,
                            emp_code=emp_code,
                            dept_name=dept_name,
                            confidence=confidence,
                            bbox=BBox(x=bbox[0], y=bbox[1],
                                      w=bbox[2]-bbox[0], h=bbox[3]-bbox[1]),
                            attendance_logged=logged,
                        ))
                    else:
                        await camera_manager.broadcast_unknown(
                            camera_id=camera_id,
                            station_id=station_id,
                            bbox={"x": bbox[0], "y": bbox[1],
                                  "w": bbox[2]-bbox[0], "h": bbox[3]-bbox[1]},
                        )
                        # Unknown face alert — increment 5-min counter, trigger if threshold reached
                        unknown_count = await increment_unknown_count(station_id)
                        threshold = await get_unknown_alert_threshold()
                        if unknown_count >= threshold:
                            await _redis.publish("omnisight:events", json.dumps({
                                "event": "unknown_face_alert",
                                "station_id": station_id,
                                "camera_id": camera_id,
                                "count": unknown_count,
                                "threshold": threshold,
                                "timestamp": datetime.now(timezone.utc).isoformat(),
                            }))
                        faces.append(FaceResult(
                            tracking_id=tracking_id,
                            status="unknown",
                            confidence=0.0,
                            bbox=BBox(x=bbox[0], y=bbox[1],
                                      w=bbox[2]-bbox[0], h=bbox[3]-bbox[1]),
                            attendance_logged=False,
                        ))

                scan = ScanResult(
                    timestamp=datetime.now(timezone.utc),
                    camera_id=camera_id,
                    faces=faces,
                )
                await websocket.send_text(scan.model_dump_json())

    except WebSocketDisconnect:
        logger.info(f"WS disconnected: camera={camera_id}")
    except Exception as e:
        logger.error(f"WS error: camera={camera_id} error={e}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        _last_processed.pop(camera_id, None)   # clean up FPS tracker
        await camera_manager.deregister(camera_id)
