"""
Attendance Service
หน้าที่: บันทึก AttendanceLog เมื่อ scan match พร้อม cooldown ป้องกัน log ซ้ำ
         + บันทึก face snapshot เป็นหลักฐาน
"""
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.redis import check_attendance_cooldown, set_attendance_cooldown
from app.models.orm import AttendanceLog

logger   = logging.getLogger(__name__)
settings = get_settings()


async def log_attendance(
    db: AsyncSession,
    employee_id: str,
    station_id: str,
    confidence_score: float,
    face_crop_jpg: Optional[bytes] = None,   # cropped face JPEG bytes from the scan frame
) -> Optional[int]:
    """
    บันทึกเวลาเข้างานของพนักงาน พร้อม snapshot ใบหน้าเป็นหลักฐาน

    Returns:
        log.id (int)  = บันทึกสำเร็จ
        None          = อยู่ใน cooldown (ไม่บันทึกซ้ำ)

    Flow:
        1. ตรวจ Redis cooldown key
        2. ถ้ายังอยู่ใน cooldown → return None
        3. INSERT attendance_logs
        4. ถ้ามี face_crop_jpg → save ลงดิสก์, set snapshot_path
        5. commit
        6. ตั้ง cooldown key TTL 5 นาที
    """
    # 1. ตรวจ cooldown
    in_cooldown = await check_attendance_cooldown(employee_id, station_id)
    if in_cooldown:
        logger.debug(f"Cooldown active — skip log: employee={employee_id}")
        return None

    # 2. INSERT attendance log
    try:
        log = AttendanceLog(
            employee_id=uuid.UUID(employee_id),
            station_id=uuid.UUID(station_id),
            timestamp=datetime.now(timezone.utc),
            confidence_score=confidence_score,
        )
        db.add(log)
        await db.flush()   # get log.id before saving file

        # 3. Save face snapshot
        if face_crop_jpg:
            try:
                today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                snap_dir = Path(settings.storage_path) / "snapshots" / today
                snap_dir.mkdir(parents=True, exist_ok=True)
                snap_path = snap_dir / f"{log.id}.jpg"
                snap_path.write_bytes(face_crop_jpg)
                log.snapshot_path = str(snap_path.resolve())
                logger.info(f"Snapshot saved: {snap_path.resolve()} ({len(face_crop_jpg)} bytes)")
            except Exception as e:
                logger.warning(f"Failed to save face snapshot: {e}")

        await db.commit()

        # 4. ตั้ง cooldown 5 นาที
        await set_attendance_cooldown(employee_id, station_id)

        logger.info(
            f"Attendance logged: employee={employee_id} "
            f"station={station_id} confidence={confidence_score:.3f} "
            f"snapshot={'yes' if face_crop_jpg else 'no'}"
        )
        return log.id

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to log attendance: {e}")
        return None
