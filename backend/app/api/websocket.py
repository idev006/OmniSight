from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from app.db.qdrant import get_qdrant_sync
from app.db.redis import get_station_filter
from app.core.config import get_settings
from app.core.face_engine import face_engine
from app.models.schemas import ScanResult, FaceResult, BBox
from qdrant_client.models import Filter, FieldCondition, MatchAny
import cv2, numpy as np, json
from datetime import datetime, timezone

router = APIRouter()
settings = get_settings()


@router.websocket("/scan/{station_id}")
async def scan_ws(websocket: WebSocket, station_id: str, token: str = Query(default="")):
    # Minimal token check — expand with full JWT validation for production
    if not token:
        await websocket.close(code=4001)
        return

    await websocket.accept()
    qdrant = get_qdrant_sync()

    try:
        while True:
            raw = await websocket.receive_bytes()

            # Decode JPEG frame
            arr = np.frombuffer(raw, np.uint8)
            frame = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            # Get embeddings + bboxes
            detections = face_engine.get_detections(frame)
            if not detections:
                await websocket.send_text(
                    ScanResult(timestamp=datetime.now(timezone.utc), faces=[]).model_dump_json()
                )
                continue

            # Build dept filter from Redis
            dept_ids = await get_station_filter(station_id)
            qdrant_filter = None
            if dept_ids:
                qdrant_filter = Filter(
                    must=[FieldCondition(key="dept_id", match=MatchAny(any=dept_ids))]
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
                    faces.append(
                        FaceResult(
                            tracking_id=tracking_id,
                            status="match",
                            employee_id=hit.payload.get("employee_id"),
                            confidence=hit.score,
                            bbox=BBox(x=bbox[0], y=bbox[1], w=bbox[2]-bbox[0], h=bbox[3]-bbox[1]),
                        )
                    )
                else:
                    faces.append(
                        FaceResult(
                            tracking_id=tracking_id,
                            status="unknown",
                            confidence=0.0,
                            bbox=BBox(x=bbox[0], y=bbox[1], w=bbox[2]-bbox[0], h=bbox[3]-bbox[1]),
                        )
                    )

            scan = ScanResult(timestamp=datetime.now(timezone.utc), faces=faces)
            await websocket.send_text(scan.model_dump_json())

    except WebSocketDisconnect:
        pass
