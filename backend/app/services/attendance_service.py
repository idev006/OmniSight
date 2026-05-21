"""
Attendance Service
──────────────────
Architecture: 2-Phase Design (Sprint 20)

Phase 1 — check_and_reserve()  [called in critical path, before send_text]
  • Parallel Redis EXISTS for all N matches in one gather
  • Parallel Redis SET cooldown for non-cooldown matches
  • Returns list[bool] — accurate attendance_logged status
  • Why set cooldown BEFORE DB write:
      prevents race condition if same employee appears in the next frame
      while async DB write is still in progress (background task)

Phase 2 — persist_attendance_batch()  [called as asyncio.create_task, after send_text]
  • Opens its own DB session (doesn't block WebSocket session)
  • Single transaction for all N records (1 flush + 1 commit)
  • Parallel snapshot saves in executor (no event loop blocking)
  • Parallel Redis publish for notification events
  • Returns nothing — errors are logged and silently dropped

Legacy: log_attendance() kept for backward compatibility (used in tests, scripts)
"""

import asyncio
import logging
import uuid
from datetime import datetime, UTC
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.postgres import async_session_factory
from app.db.redis import (
    check_attendance_cooldown,
    set_attendance_cooldown,
)
from app.models.orm import AttendanceLog

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Phase 1: Check & Reserve ──────────────────────────────────────────────────


async def check_and_reserve(
    matches: list[tuple[str, str, float]],  # [(employee_id, station_id, confidence)]
) -> list[bool]:
    """
    Fast path — Redis only, no DB, called BEFORE send_text().

    For each match:
      1. EXISTS cooldown key  → parallel gather
      2. SET cooldown key (TTL)  → parallel gather for non-cooldown matches

    By setting the cooldown key BEFORE the DB write (which happens in the background),
    we guarantee that even if the same employee appears in the NEXT frame while the DB
    write is still in-flight, they won't be double-logged.

    Returns: list[bool] where True = "will be logged" (reservation made)
    """
    if not matches:
        return []

    # Parallel cooldown existence checks
    in_cooldown_list: list[bool] = list(
        await asyncio.gather(*[check_attendance_cooldown(emp_id, station_id) for emp_id, station_id, _ in matches])
    )

    # Parallel cooldown SET for matches that will be logged
    # This is the "reservation" — prevents double-logging across frames
    reserve_tasks = [
        set_attendance_cooldown(emp_id, station_id)
        for (emp_id, station_id, _), in_cd in zip(matches, in_cooldown_list, strict=False)
        if not in_cd
    ]
    if reserve_tasks:
        await asyncio.gather(*reserve_tasks)

    return [not in_cd for in_cd in in_cooldown_list]


# ── Phase 2: Persist (background task) ───────────────────────────────────────


async def persist_attendance_batch(
    to_persist: list[dict],
) -> None:
    """
    Background task — called via asyncio.create_task() AFTER send_text().

    Each item in to_persist:
        employee_id:      str
        station_id:       str
        confidence_score: float
        face_crop_jpg:    bytes | None

    Design:
    - Own DB session (doesn't share WebSocket handler's session)
    - Single transaction for all N records (1 flush + 1 commit)
    - Snapshot disk writes run in executor (never block event loop)
    - Errors are logged and silently dropped (attendance already reserved in Redis)
    """
    if not to_persist:
        return

    loop = asyncio.get_event_loop()

    async with async_session_factory() as db:
        try:
            # ── INSERT all records ──────────────────────────────────────────
            logs: list[tuple[AttendanceLog, dict]] = []
            for m in to_persist:
                log = AttendanceLog(
                    employee_id=uuid.UUID(m["employee_id"]),
                    station_id=uuid.UUID(m["station_id"]),
                    timestamp=datetime.now(UTC),
                    confidence_score=m["confidence_score"],
                )
                db.add(log)
                logs.append((log, m))

            # Single flush → get all IDs in one round-trip
            await db.flush()

            # ── Save snapshots in parallel (executor — non-blocking) ────────
            async def _save_snapshot(log: AttendanceLog, m: dict) -> None:
                face_crop = m.get("face_crop_jpg")
                if not face_crop:
                    return
                try:
                    today = datetime.now(UTC).strftime("%Y-%m-%d")
                    snap_dir = Path(settings.storage_path) / "snapshots" / today
                    snap_dir.mkdir(parents=True, exist_ok=True)
                    snap_path = snap_dir / f"{log.id}.jpg"
                    # write_bytes is sync — run in executor, never block event loop
                    await loop.run_in_executor(None, snap_path.write_bytes, face_crop)
                    log.snapshot_path = str(snap_path.resolve())
                    logger.debug("Snapshot saved: %s (%d bytes)", snap_path, len(face_crop))
                except Exception as exc:
                    logger.warning("Snapshot save failed for log %s: %s", log.id, exc)

            await asyncio.gather(*[_save_snapshot(log, m) for log, m in logs])

            # Single commit for all records
            await db.commit()

            for log, m in logs:
                logger.info(
                    "Attendance persisted: employee=%s station=%s " "confidence=%.3f log_id=%s snapshot=%s",
                    m["employee_id"],
                    m["station_id"],
                    m["confidence_score"],
                    log.id,
                    "yes" if m.get("face_crop_jpg") else "no",
                )

        except Exception as exc:
            await db.rollback()
            logger.error("persist_attendance_batch failed: %s", exc)
            # Note: cooldown keys are already set (phase 1 reserved them)
            # So employees won't be double-logged even if DB write fails


# ── Legacy: single-record log (backward compat) ───────────────────────────────


async def log_attendance(
    db: AsyncSession,
    employee_id: str,
    station_id: str,
    confidence_score: float,
    face_crop_jpg: bytes | None = None,
) -> int | None:
    """
    Legacy single-record attendance log.
    Used by tests and one-off scripts.
    Production WebSocket handler uses check_and_reserve() + persist_attendance_batch().
    """
    in_cooldown = await check_attendance_cooldown(employee_id, station_id)
    if in_cooldown:
        return None

    loop = asyncio.get_event_loop()

    try:
        log = AttendanceLog(
            employee_id=uuid.UUID(employee_id),
            station_id=uuid.UUID(station_id),
            timestamp=datetime.now(UTC),
            confidence_score=confidence_score,
        )
        db.add(log)
        await db.flush()

        if face_crop_jpg:
            try:
                today = datetime.now(UTC).strftime("%Y-%m-%d")
                snap_dir = Path(settings.storage_path) / "snapshots" / today
                snap_dir.mkdir(parents=True, exist_ok=True)
                snap_path = snap_dir / f"{log.id}.jpg"
                # FIX: run in executor — was blocking event loop with sync write_bytes
                await loop.run_in_executor(None, snap_path.write_bytes, face_crop_jpg)
                log.snapshot_path = str(snap_path.resolve())
            except Exception as exc:
                logger.warning("Snapshot save failed: %s", exc)

        await db.commit()
        await set_attendance_cooldown(employee_id, station_id)
        return log.id

    except Exception as exc:
        await db.rollback()
        logger.error("log_attendance failed: %s", exc)
        return None
