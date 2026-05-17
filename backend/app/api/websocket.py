import logging
from datetime import datetime, timezone

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from qdrant_client.models import Filter, FieldCondition, MatchAny
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.face_engine import face_engine
from app.db.postgres import async_session_factory
from app.db.qdrant import get_qdrant_sync
from app.db.redis import get_station_filter
from app.models.schemas import BBox, FaceResult, ScanResult
from app.services.attendance_service import log_attendance

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()


@router.websocket("/scan/{station_id}")
async def scan_ws(
    websocket: WebSocket,
    station_id: str,
    token: str = Query(default=""),
):
    # ── Auth (minimal — จะ upgrade เป็น full JWT ใน Sprint User Management) ──
    if not token:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    logger.info(f"WebSocket connected: station={station_id}")

    qdrant = get_qdrant_sync()

    try:
        async with async_session_factory() as db:
            while True:
                # 1. รับ binary JPEG frame จาก browser/agent
                raw = await websocket.receive_bytes()

                # 2. Decode JPEG → numpy BGR array
                arr = np.frombuffer(raw, np.uint8)
                frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
                if frame is None:
                    continue

                # 3. Face detection + embedding (ONNX inference)
                detections = face_engine.get_detections(frame)
                if not detections:
                    await websocket.send_text(
                        ScanResult(
                            timestamp=datetime.now(timezone.utc),
                            faces=[],
                        ).model_dump_json()
                    )
                    continue

                # 4. ดึง dept filter จาก Redis (< 1ms)
                dept_ids = await get_station_filter(station_id)
                qdrant_filter = None
                if dept_ids:
                    qdrant_filter = Filter(
                        must=[
                            FieldCondition(
                                key="dept_id",
                                match=MatchAny(any=dept_ids),
                            )
                        ]
                    )

                # 5. ค้นหาและบันทึก attendance สำหรับแต่ละหน้า
                faces: list[FaceResult] = []

                for tracking_id, embedding, bbox in detections:
                    # Vector search ใน Qdrant
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

                        # บันทึก attendance (พร้อม cooldown 5 นาที)
                        logged = await log_attendance(
                            db=db,
                            employee_id=employee_id,
                            station_id=station_id,
                            confidence_score=confidence,
                        )

                        faces.append(
                            FaceResult(
                                tracking_id=tracking_id,
                                status="match",
                                employee_id=employee_id,
                                confidence=confidence,
                                bbox=BBox(
                                    x=bbox[0],
                                    y=bbox[1],
                                    w=bbox[2] - bbox[0],
                                    h=bbox[3] - bbox[1],
                                ),
                                attendance_logged=logged,
                            )
                        )
                    else:
                        faces.append(
                            FaceResult(
                                tracking_id=tracking_id,
                                status="unknown",
                                confidence=0.0,
                                bbox=BBox(
                                    x=bbox[0],
                                    y=bbox[1],
                                    w=bbox[2] - bbox[0],
                                    h=bbox[3] - bbox[1],
                                ),
                                attendance_logged=False,
                            )
                        )

                # 6. ส่งผลลัพธ์กลับ browser
                scan = ScanResult(
                    timestamp=datetime.now(timezone.utc),
                    faces=faces,
                )
                await websocket.send_text(scan.model_dump_json())

    except WebSocketDisconnect:
        logger.info(f"WebSocket disconnected: station={station_id}")
    except Exception as e:
        logger.error(f"WebSocket error: station={station_id} error={e}")
        await websocket.close(code=1011)
