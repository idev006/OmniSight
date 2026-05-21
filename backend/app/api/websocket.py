"""
WebSocket Scan Handler — Multi-Camera Edition
ws/scan/{station_id}?token={jwt}&camera_id={id}

Performance architecture (Sprint 15):
  1. FPS gate              — drop frames faster than max_fps, no queue buildup
  2. Thread pool executor  — CPU-bound ONNX off the event loop
  3. AsyncQdrantClient     — Qdrant search as pure async IO (zero threads)
  4. search_batch()        — 1 HTTP round-trip for all N faces per frame
  5. Anti-spoof batch      — 1 ONNX call for all N faces per frame
  6. Settings cache 5s TTL — asyncio.Lock prevents stampede on cache expiry
  7. Decode in executor    — cv2.imdecode off event loop
  8. IoU tracker cache     — skip full pipeline for same face in consecutive frames
  9. Prometheus metrics    — latency histograms, counters, gauges
 10. Dynamic worker scaling — executor resized without restart when setting changes
"""

import asyncio
import json
import logging
import time
from concurrent.futures import ThreadPoolExecutor
from functools import partial

import cv2
import numpy as np
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from qdrant_client.models import Filter, FieldCondition, MatchAny, SearchRequest
from sqlalchemy import select

from app.core.config import get_settings
from app.core.security import get_current_user_ws
from app.core.face_engine import face_engine, anti_spoof_engine, crop_face_jpeg
from app.core.tracker import FaceTracker
from app.core.metrics import (
    INF_DURATION,
    QDRANT_DURATION,
    SPOOF_DURATION,
    FRAMES_RECEIVED,
    FRAMES_PROCESSED,
    FRAMES_DROPPED,
    CACHE_HITS,
    CACHE_MISSES,
    FACES_DETECTED,
    FACES_MATCHED,
    FACES_UNKNOWN,
    FACES_SPOOF,
    ACTIVE_CAMERAS,
    INFERENCE_WORKERS,
    INFLIGHT_INFERENCES,
)
from app.db.postgres import async_session_factory
from app.db.qdrant import qdrant as _async_qdrant
from app.db.redis import (
    get_station_filter,
    redis as _redis,
    increment_unknown_count,
    get_unknown_alert_threshold,
    get_anti_spoof_enabled,
    get_anti_spoof_threshold,
)
from app.models.orm import Employee, Department
from app.models.schemas import BBox, FaceResult, ScanResult
from app.services.attendance_service import check_and_reserve, persist_attendance_batch
from app.services.camera_manager import camera_manager
from datetime import datetime, UTC

logger = logging.getLogger(__name__)
router = APIRouter()
settings = get_settings()

# ── Thread pool — CPU-only: detection, anti-spoof, decode, crop ───────────────
# Dynamic scaling: the pool is swapped atomically when inference_workers changes.
# asyncio.Lock prevents two coroutines from rebuilding the pool simultaneously.
_executor: ThreadPoolExecutor = ThreadPoolExecutor(
    max_workers=settings.inference_workers,
    thread_name_prefix="face-worker",
)
_executor_workers: int = settings.inference_workers
_executor_lock = asyncio.Lock()
INFERENCE_WORKERS.set(settings.inference_workers)


async def _resize_executor_if_needed(new_size: int) -> None:
    """
    Atomically swap the global ThreadPoolExecutor when inference_workers changes.
    Old executor is shut down gracefully (running tasks finish; new tasks go to
    the new pool).  asyncio.Lock ensures only one resize runs at a time.
    """
    global _executor, _executor_workers
    if new_size == _executor_workers:
        return
    async with _executor_lock:
        if new_size == _executor_workers:  # someone else already resized
            return
        old = _executor
        _executor = ThreadPoolExecutor(max_workers=new_size, thread_name_prefix="face-worker")
        _executor_workers = new_size
        INFERENCE_WORKERS.set(new_size)
        old.shutdown(wait=False)  # existing tasks finish; no new ones
        logger.info(f"Executor resized → {new_size} workers")


# ── Per-camera state (process lifetime) ──────────────────────────────────────
_last_processed: dict[str, float] = {}
_trackers: dict[str, FaceTracker] = {}

# ── Global settings cache (5-second TTL, stampede-safe) ──────────────────────
_cached_settings: dict = {}
_cached_settings_ts: float = 0.0
_SETTINGS_TTL: float = 5.0
_settings_lock = asyncio.Lock()


async def _get_max_fps() -> float:
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


async def _get_frame_settings() -> dict:
    """
    Cached settings dict, refreshed from Redis at most once per TTL.
    Double-checked asyncio.Lock: only one coroutine fires the Redis gather
    even when all N camera handlers hit an expired cache simultaneously.
    Also triggers dynamic executor resize if inference_workers changed.
    """
    global _cached_settings, _cached_settings_ts
    now = time.monotonic()
    if now - _cached_settings_ts <= _SETTINGS_TTL:
        return _cached_settings

    async with _settings_lock:
        if now - _cached_settings_ts <= _SETTINGS_TTL:
            return _cached_settings
        vals = await asyncio.gather(
            _get_max_fps(),
            _get_match_threshold(),
            get_anti_spoof_enabled(),
            get_anti_spoof_threshold(),
            get_unknown_alert_threshold(),
            _redis.get("setting:inference_workers"),
            _redis.get("setting:recognition_cache_ttl"),
        )
        raw_cache_ttl = vals[6]
        _cached_settings = {
            "max_fps": vals[0],
            "match_threshold": vals[1],
            "spoof_enabled": vals[2] and anti_spoof_engine.available,
            "spoof_threshold": vals[3],
            "unknown_threshold": vals[4],
            # recognition_cache_ttl: how long a Qdrant result is reused per tracking_id
            # Default 30 s — safe because if the person leaves, the track expires in 2 s
            # and the next person gets a fresh tracking_id → fresh Qdrant search.
            "recognition_cache_ttl": max(5.0, float(raw_cache_ttl)) if raw_cache_ttl else 30.0,
        }
        # Dynamic worker scaling — resize executor if admin changed the setting
        raw_workers = vals[5]
        if raw_workers:
            await _resize_executor_if_needed(max(1, int(raw_workers)))

        _cached_settings_ts = time.monotonic()
    return _cached_settings


@router.websocket("/scan/{station_id}")
async def scan_ws(
    websocket: WebSocket,
    station_id: str,
    token: str = Query(default=""),
    camera_id: str = Query(default=""),
):
    # ── Auth ─────────────────────────────────────────────────────────────────
    try:
        user = get_current_user_ws(token)
    except Exception:
        await websocket.close(code=4001, reason="Unauthorized")
        return

    if not user.can_access_station(station_id):
        await websocket.close(code=4003, reason="No access to this station")
        return

    if not camera_id:
        prefix = "sm" if user.role == "OPERATOR" else "wc"
        camera_id = f"{prefix}-{user.user_id[:6]}-{station_id[:6]}"

    camera_type = "SMARTPHONE" if user.role == "OPERATOR" else "WEBCAM"

    await websocket.accept()
    logger.info(f"WS connected: camera={camera_id} station={station_id} user={user.username}")

    await camera_manager.register(
        camera_id=camera_id,
        station_id=station_id,
        camera_type=camera_type,
        websocket=websocket,
    )
    ACTIVE_CAMERAS.inc()

    loop = asyncio.get_event_loop()

    try:
        while True:
            raw = await websocket.receive_bytes()
            FRAMES_RECEIVED.inc()
            camera_manager.record_frame(camera_id)

            conn = camera_manager._connections.get(camera_id)
            if conn and conn.status == "paused":
                continue

            cfg = await _get_frame_settings()
            min_interval = 1.0 / cfg["max_fps"]

            now = time.monotonic()
            if now - _last_processed.get(camera_id, 0.0) < min_interval:
                FRAMES_DROPPED.inc()
                continue
            _last_processed[camera_id] = now
            FRAMES_PROCESSED.inc()

            # Decode JPEG in executor
            arr = np.frombuffer(raw, np.uint8)
            frame = await loop.run_in_executor(_executor, cv2.imdecode, arr, cv2.IMREAD_COLOR)
            if frame is None:
                continue

            # Face detection — timed for Prometheus histogram
            INFLIGHT_INFERENCES.inc()
            t0 = time.perf_counter()
            try:
                detections = await loop.run_in_executor(_executor, face_engine.get_detections, frame)
            finally:
                INF_DURATION.observe(time.perf_counter() - t0)
                INFLIGHT_INFERENCES.dec()

            FACES_DETECTED.inc(len(detections))

            if not detections:
                await websocket.send_text(
                    ScanResult(timestamp=datetime.now(UTC), camera_id=camera_id, faces=[]).model_dump_json()
                )
                continue

            # Hungarian tracker — globally optimal assignment
            tracker = _trackers.setdefault(camera_id, FaceTracker())
            tracked = tracker.update([(emb, bbox) for _, emb, bbox in detections])

            dept_ids = await get_station_filter(station_id)
            qdrant_filter = (
                Filter(must=[FieldCondition(key="dept_id", match=MatchAny(any=dept_ids))]) if dept_ids else None
            )

            match_threshold = cfg["match_threshold"]
            spoof_enabled = cfg["spoof_enabled"]
            spoof_threshold = cfg["spoof_threshold"]

            # ── Step 1: cached vs needs full pipeline ─────────────────────────
            faces: list[FaceResult] = []
            to_process: list[tuple[int, np.ndarray, list[int]]] = []

            cache_ttl = cfg["recognition_cache_ttl"]
            for tid, emb, bbox in tracked:
                cached = tracker.get_cached_result(tid, ttl=cache_ttl)
                if cached is not None:
                    CACHE_HITS.inc()
                    faces.append(
                        cached.model_copy(
                            update={
                                "tracking_id": tid,
                                "bbox": BBox(x=bbox[0], y=bbox[1], w=bbox[2] - bbox[0], h=bbox[3] - bbox[1]),
                                "attendance_logged": False,
                            }
                        )
                    )
                else:
                    CACHE_MISSES.inc()
                    to_process.append((tid, emb, bbox))

            if not to_process:
                await websocket.send_text(
                    ScanResult(timestamp=datetime.now(UTC), camera_id=camera_id, faces=faces).model_dump_json()
                )
                continue

            # ── Step 2: batch anti-spoof (1 ONNX call for all N faces) ────────
            if spoof_enabled:
                t0 = time.perf_counter()
                bboxes = [b for _, _, b in to_process]
                scores = await loop.run_in_executor(_executor, anti_spoof_engine.predict_batch, frame, bboxes)
                SPOOF_DURATION.observe(time.perf_counter() - t0)
                spoof_checks = [(s >= spoof_threshold, s) for s in scores]
            else:
                spoof_checks = [(True, 1.0)] * len(to_process)

            # ── Step 3: live vs spoof ──────────────────────────────────────────
            live: list[tuple[int, np.ndarray, list[int]]] = []
            for i, (tid, emb, bbox) in enumerate(to_process):
                is_live, score = spoof_checks[i]
                if not is_live:
                    FACES_SPOOF.inc()
                    logger.warning(
                        "Anti-spoof REJECTED: camera=%s score=%.3f threshold=%.3f",
                        camera_id,
                        score,
                        spoof_threshold,
                    )
                    r = FaceResult(
                        tracking_id=tid,
                        status="spoof",
                        confidence=score,
                        bbox=BBox(x=bbox[0], y=bbox[1], w=bbox[2] - bbox[0], h=bbox[3] - bbox[1]),
                        attendance_logged=False,
                    )
                    tracker.set_result(tid, r)
                    faces.append(r)
                    await _redis.publish(
                        "omnisight:events",
                        json.dumps(
                            {
                                "event": "spoof_detected",
                                "station_id": station_id,
                                "camera_id": camera_id,
                                "timestamp": datetime.now(UTC).isoformat(),
                            }
                        ),
                    )
                else:
                    live.append((tid, emb, bbox))

            # ── Step 4: Qdrant batch search (1 HTTP request for all N faces) ───
            if live:
                t0 = time.perf_counter()
                batch_results = await _async_qdrant.search_batch(
                    collection_name=settings.qdrant_collection,
                    requests=[
                        SearchRequest(
                            vector=emb.tolist(),
                            filter=qdrant_filter,
                            limit=1,
                            score_threshold=match_threshold,
                            with_payload=True,
                        )
                        for _, emb, _ in live
                    ],
                )
                QDRANT_DURATION.observe(time.perf_counter() - t0)
            else:
                batch_results = []

            # ── Step 5: matches vs unknowns ────────────────────────────────────
            matches: list[tuple[int, list[int], str, float]] = []
            unknowns: list[tuple[int, list[int]]] = []
            for i, (tid, _, bbox) in enumerate(live):
                hits = batch_results[i] if i < len(batch_results) else []
                if hits:
                    matches.append((tid, bbox, hits[0].payload["employee_id"], hits[0].score))
                else:
                    unknowns.append((tid, bbox))

            # ── Step 6: DB lookup (1 query, IN clause) + crop faces ────────────
            if matches:
                async with async_session_factory() as db:
                    emp_result = await db.execute(
                        select(Employee, Department.name.label("dept_name"))
                        .join(Department, Department.id == Employee.dept_id, isouter=True)
                        .where(Employee.id.in_([emp_id for _, _, emp_id, _ in matches]))
                    )
                    emp_map = {str(row[0].id): row for row in emp_result.all()}

                crops = await asyncio.gather(
                    *[
                        loop.run_in_executor(_executor, partial(crop_face_jpeg, frame, bbox))
                        for _, bbox, _, _ in matches
                    ]
                )
            else:
                emp_map, crops = {}, []

            # ── Step 7 (Phase 1): Check & Reserve attendance ───────────────────
            # FAST PATH: parallel Redis only — no DB write yet
            # • EXISTS cooldown × N  → parallel gather
            # • SET cooldown × N     → parallel gather (set NOW, before DB write)
            # attendance_logged in FaceResult is ACCURATE because slot is reserved
            match_tuples = [(emp_id, station_id, conf) for _, _, emp_id, conf in matches]
            will_log_list = await check_and_reserve(match_tuples) if matches else []

            # Build FaceResult for matches
            persist_list: list[dict] = []
            broadcast_matches: list[dict] = []

            for i, (tid, bbox, emp_id, confidence) in enumerate(matches):
                row = emp_map.get(emp_id)
                full_name = row[0].full_name or "" if row else ""
                emp_code = row[0].emp_code if row else None
                dept_name = row[1] if row else None
                will_log = will_log_list[i] if i < len(will_log_list) else False

                FACES_MATCHED.inc()
                r = FaceResult(
                    tracking_id=tid,
                    status="match",
                    employee_id=emp_id,
                    full_name=full_name,
                    emp_code=emp_code,
                    dept_name=dept_name,
                    confidence=confidence,
                    bbox=BBox(x=bbox[0], y=bbox[1], w=bbox[2] - bbox[0], h=bbox[3] - bbox[1]),
                    attendance_logged=will_log,
                )
                tracker.set_result(tid, r)
                faces.append(r)

                if will_log:
                    persist_list.append(
                        {
                            "employee_id": emp_id,
                            "station_id": station_id,
                            "confidence_score": confidence,
                            "face_crop_jpg": crops[i] if crops else None,
                        }
                    )
                broadcast_matches.append(
                    {
                        "employee_id": emp_id,
                        "full_name": full_name,
                        "emp_code": emp_code,
                        "dept_name": dept_name,
                        "confidence": confidence,
                        "logged": will_log,
                    }
                )

            # ── Step 8: unknowns ───────────────────────────────────────────────
            unknown_publishes: list[dict] = []
            for tid, bbox in unknowns:
                FACES_UNKNOWN.inc()
                unknown_count = await increment_unknown_count(station_id)
                r = FaceResult(
                    tracking_id=tid,
                    status="unknown",
                    confidence=0.0,
                    bbox=BBox(x=bbox[0], y=bbox[1], w=bbox[2] - bbox[0], h=bbox[3] - bbox[1]),
                    attendance_logged=False,
                )
                tracker.set_result(tid, r)
                faces.append(r)
                unknown_publishes.append(
                    {
                        "count": unknown_count,
                        "bbox": {"x": bbox[0], "y": bbox[1], "w": bbox[2] - bbox[0], "h": bbox[3] - bbox[1]},
                    }
                )

            # ── SEND result FIRST — end of critical path ───────────────────────
            await websocket.send_text(
                ScanResult(timestamp=datetime.now(UTC), camera_id=camera_id, faces=faces).model_dump_json()
            )

            # ── Step 9 (Phase 2): Background persist + broadcast ───────────────
            # create_task → fire-and-forget, next frame starts immediately
            asyncio.create_task(
                _persist_and_broadcast(
                    persist_list=persist_list,
                    broadcast_matches=broadcast_matches,
                    unknown_publishes=unknown_publishes,
                    station_id=station_id,
                    camera_id=camera_id,
                    cfg=cfg,
                    ts=datetime.now(UTC).isoformat(),
                    emp_map_snapshot={k: (v[0].full_name, v[0].emp_code, v[1]) for k, v in emp_map.items()},
                )
            )

    except WebSocketDisconnect:
        logger.info(f"WS disconnected: camera={camera_id}")
    except Exception as e:
        logger.error(f"WS error: camera={camera_id} error={e}")
        try:
            await websocket.close(code=1011)
        except Exception:
            pass
    finally:
        _last_processed.pop(camera_id, None)
        _trackers.pop(camera_id, None)
        ACTIVE_CAMERAS.dec()
        await camera_manager.deregister(camera_id)


# ── Background task: persist + broadcast (Phase 2) ───────────────────────────


async def _persist_and_broadcast(
    persist_list: list[dict],
    broadcast_matches: list[dict],
    unknown_publishes: list[dict],
    station_id: str,
    camera_id: str,
    cfg: dict,
    ts: str,
    emp_map_snapshot: dict,  # {emp_id: (full_name, emp_code, dept_name)}
) -> None:
    """
    Phase 2 — runs AFTER send_text(), never delays frontend response.

    1. persist_attendance_batch → own DB session, single transaction for all N
    2. Broadcast match events to Pilot Console  → asyncio.gather (parallel)
    3. Redis publish attendance_match events    → asyncio.gather (parallel)
    4. Broadcast unknown events                → asyncio.gather (parallel)
    5. Redis publish unknown_face_alert        → asyncio.gather (parallel)

    All errors are caught and logged — never raise to caller.
    """
    try:
        # ── Persist all new attendances (own session, batch) ─────────────────
        if persist_list:
            await persist_attendance_batch(persist_list)

        # ── Broadcast + publish matches in parallel ───────────────────────────
        match_tasks = []
        publish_tasks = []
        for m in broadcast_matches:
            match_tasks.append(
                camera_manager.broadcast_attendance(
                    camera_id=camera_id,
                    station_id=station_id,
                    employee_id=m["employee_id"],
                    full_name=m["full_name"],
                    confidence=m["confidence"],
                    logged=m["logged"],
                )
            )
            if m["logged"]:
                publish_tasks.append(
                    _redis.publish(
                        "omnisight:events",
                        json.dumps(
                            {
                                "event": "attendance_match",
                                "station_id": station_id,
                                "camera_id": camera_id,
                                "employee_id": m["employee_id"],
                                "full_name": m["full_name"],
                                "emp_code": m["emp_code"],
                                "dept_name": m["dept_name"],
                                "confidence": round(m["confidence"], 4),
                                "timestamp": ts,
                            }
                        ),
                    )
                )

        # ── Broadcast + publish unknowns in parallel ──────────────────────────
        for u in unknown_publishes:
            match_tasks.append(
                camera_manager.broadcast_unknown(
                    camera_id=camera_id,
                    station_id=station_id,
                    bbox=u["bbox"],
                )
            )
            if u["count"] >= cfg["unknown_threshold"]:
                publish_tasks.append(
                    _redis.publish(
                        "omnisight:events",
                        json.dumps(
                            {
                                "event": "unknown_face_alert",
                                "station_id": station_id,
                                "camera_id": camera_id,
                                "count": u["count"],
                                "threshold": cfg["unknown_threshold"],
                                "timestamp": ts,
                            }
                        ),
                    )
                )

        # Run all IO in parallel
        await asyncio.gather(*match_tasks, *publish_tasks, return_exceptions=True)

    except Exception as exc:
        logger.error("_persist_and_broadcast failed: camera=%s error=%s", camera_id, exc)
