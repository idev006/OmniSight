"""
WebSocket Scan Handler — Multi-Camera Edition
ws/scan/{station_id}?token={jwt}&camera_id={id}
"""
import logging
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from qdrant_client.models import Filter, FieldCondition, MatchAny

from app.core.config import get_settings
from app.core.security import get_current_user_ws
from app.core.face_engine import face_engine
from app.db.postgres import async_session_factory
from app.db.qdrant import get_qdrant_sync
from app.db.redis import get_station_filter
from app.models.schemas import BBox, FaceResult, ScanResult
from app.services.attendance_service import log_attendance
from app.services.camera_manager import camera_manager

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


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

    # ── Camera ID ─────────────────────────────────────────────────────────────
    # ถ้าไม่ส่ง camera_id → ใช้ user_id เป็น default (เหมาะสำหรับ webcam/smartphone)
    if not camera_id:
        camera_id = f"{user.user_id[:8]}-{station_id[:8]}"

    # Detect camera type from user role / token
    camera_type = "SMARTPHONE" if user.role == "OPERATOR" else "WEBCAM"

    await websocket.accept()
    logger.info(f"WS connected: camera={camera_id} station={station_id} user={user.username}")

    # ── Register camera (hot plug) ─────────────────────────────────────────────
    await camera_manager.register(
        camera_id=camera_id,
        station_id=station_id,
        camera_type=camera_type,
        websocket=websocket,
    )

    qdrant = get_qdrant_sync()
    paused = False

    try:
        async with async_session_factory() as db:
            while True:
                # รับ frame
                raw = await websocket.receive_bytes()

                # Update FPS tracker
                camera_manager.record_frame(camera_id)

                # Handle pause state
                if paused:
                    continue

                # Decode JPEG
                arr = np.frombuffer(raw, np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                # Face detection
                detections = face_engine.get_detections(frame)
                if not detections:
                    await websocket.send_text(
                        ScanResult(
                            timestamp=datetime.now(timezone.utc),
                            camera_id=camera_id,
                            faces=[],
                        ).model_dump_json()
                    )
                    continue

                # Station dept filter (Redis < 1ms)
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

                for tracking_id, embedding, bbox in detections:
                    results = qdrant.search(
                        collection_name=settings.qdrant_collection,
                        query_vector=embedding.tolist(),
                        query_filter=qdrant_filter,
                        limit=1,
                        score_threshold=settings.match_threshold,
                    )

                    if results:
                        hit = results[0]
                        employee_id = hit.payload.get("employee_id")
                        confidence = hit.score
                        full_name = hit.payload.get("full_name", "")

                        logged = await log_attendance(
                            db=db,
                            employee_id=employee_id,
                            station_id=station_id,
                            confidence_score=confidence,
                        )

                        # Broadcast to Pilot Console
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
                            confidence=confidence,
                            bbox=BBox(x=bbox[0], y=bbox[1],
                                      w=bbox[2]-bbox[0], h=bbox[3]-bbox[1]),
                            attendance_logged=logged,
                        ))
                    else:
                        # Unknown face — broadcast alert
                        await camera_manager.broadcast_unknown(
                            camera_id=camera_id,
                            station_id=station_id,
                            bbox={"x": bbox[0], "y": bbox[1],
                                  "w": bbox[2]-bbox[0], "h": bbox[3]-bbox[1]},
                        )
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
        # Hot deregister
        await camera_manager.deregister(camera_id)
