"""
Absent alert service — detects employees who missed their shift and publishes
absent_alert events to omnisight:events (Redis Pub/Sub).

Logic:
  Every CHECK_INTERVAL seconds, for each employee with a shift today:
    - If shift_start + late_threshold_minutes has passed (they are "officially" absent)
    - AND they have no attendance log today
    - AND they haven't been notified yet today (Redis set: absent_notified:{date})
  → publish absent_alert event and mark as notified

Settings read from Redis:
  late_threshold_minutes   (default 15)
  notify_on_absent         (default 1)
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select, cast, Date, func
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 300  # seconds between scans (5 minutes)


async def absent_alert_loop(redis) -> None:
    """Background task — start from main.py lifespan."""
    logger.info("AbsentAlertService: started (interval=%ds)", CHECK_INTERVAL)
    try:
        while True:
            await asyncio.sleep(CHECK_INTERVAL)
            try:
                await _check_absences(redis)
            except Exception as e:
                logger.warning("AbsentAlertService scan error: %s", e)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("AbsentAlertService: stopped")


async def _check_absences(redis) -> None:
    from app.db.postgres import async_session_factory
    from app.models.orm import Employee, Shift, Department, AttendanceLog

    if await redis.get("setting:notify_on_absent") == "0":
        return

    late_val = await redis.get("setting:late_threshold_minutes")
    late_threshold = int(late_val) if late_val else 15

    today = datetime.now(timezone.utc).date()
    now   = datetime.now(timezone.utc)

    notified_key = f"absent_notified:{today.isoformat()}"

    async with async_session_factory() as db:
        emp_rows = await db.execute(
            select(Employee, Shift, Department.name.label("dept_name"))
            .join(Shift, Shift.id == Employee.shift_id)
            .join(Department, Department.id == Employee.dept_id, isouter=True)
            .where(Employee.is_active == True)
        )
        employees = emp_rows.all()

        # Build set of employee_ids who checked in today
        checked_in = await db.execute(
            select(AttendanceLog.employee_id)
            .where(cast(AttendanceLog.timestamp, Date) == today)
            .distinct()
        )
        checked_ids = {row[0] for row in checked_in}

    for emp, shift, dept_name in employees:
        shift_start = datetime.combine(today, shift.start_time, tzinfo=timezone.utc)
        cutoff = shift_start + timedelta(minutes=late_threshold)

        if now < cutoff:
            continue  # shift hasn't reached absent cutoff yet

        if emp.id in checked_ids:
            continue  # employee already checked in

        already_notified = await redis.sismember(notified_key, str(emp.id))
        if already_notified:
            continue

        event = {
            "event":       "absent_alert",
            "employee_id": str(emp.id),
            "emp_code":    emp.emp_code,
            "full_name":   emp.full_name,
            "dept_name":   dept_name or "",
            "shift_name":  shift.name,
            "shift_start": shift.start_time.strftime("%H:%M"),
            "timestamp":   now.isoformat(),
        }
        await redis.publish("omnisight:events", json.dumps(event))
        await redis.sadd(notified_key, str(emp.id))
        await redis.expire(notified_key, 86400)  # auto-clean after 24h

        logger.info(
            "AbsentAlertService: absent_alert published for %s (%s)",
            emp.full_name, emp.emp_code,
        )
