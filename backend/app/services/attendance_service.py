"""
Attendance Service
หน้าที่: บันทึก AttendanceLog เมื่อ scan match พร้อม cooldown ป้องกัน log ซ้ำ
"""
import logging
import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.redis import check_attendance_cooldown, set_attendance_cooldown
from app.models.orm import AttendanceLog

logger = logging.getLogger(__name__)


async def log_attendance(
    db: AsyncSession,
    employee_id: str,
    station_id: str,
    confidence_score: float,
) -> bool:
    """
    บันทึกเวลาเข้างานของพนักงาน

    Returns:
        True  = บันทึกสำเร็จ
        False = อยู่ใน cooldown (ไม่บันทึกซ้ำ)

    Flow:
        1. ตรวจ Redis cooldown key
        2. ถ้ายังอยู่ใน cooldown → return False
        3. INSERT attendance_logs
        4. ตั้ง cooldown key TTL 5 นาที
    """
    # 1. ตรวจ cooldown
    in_cooldown = await check_attendance_cooldown(employee_id, station_id)
    if in_cooldown:
        logger.debug(f"Cooldown active — skip log: employee={employee_id}")
        return False

    # 2. INSERT attendance log
    try:
        log = AttendanceLog(
            employee_id=uuid.UUID(employee_id),
            station_id=uuid.UUID(station_id),
            timestamp=datetime.now(timezone.utc),
            confidence_score=confidence_score,
        )
        db.add(log)
        await db.commit()

        # 3. ตั้ง cooldown 5 นาที
        await set_attendance_cooldown(employee_id, station_id)

        logger.info(
            f"Attendance logged: employee={employee_id} "
            f"station={station_id} confidence={confidence_score:.3f}"
        )
        return True

    except Exception as e:
        await db.rollback()
        logger.error(f"Failed to log attendance: {e}")
        return False
