from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from sqlalchemy.orm import selectinload
from app.db.postgres import get_db
from app.models.orm import AttendanceLog, Employee, Station, Department
from app.core.security import require_hr, CurrentUser
from datetime import date, datetime, timezone
from pathlib import Path
import calendar

router = APIRouter()


@router.get("")
async def list_attendance(
    date: date = Query(default=None),
    dept_id: int = Query(default=None),
    limit: int = Query(default=100, le=1000),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    q = (
        select(AttendanceLog)
        .options(
            selectinload(AttendanceLog.employee).selectinload(Employee.department),
            selectinload(AttendanceLog.station),
        )
        .order_by(AttendanceLog.timestamp.desc())
        .limit(limit)
    )

    if date:
        start = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
        end = datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=timezone.utc)
        q = q.where(AttendanceLog.timestamp.between(start, end))

    if dept_id:
        q = q.join(AttendanceLog.employee).where(Employee.dept_id == dept_id)

    result = await db.execute(q)
    logs = result.scalars().all()

    return [
        {
            "id": log.id,
            "employee_id": log.employee_id,
            "emp_code": log.employee.emp_code if log.employee else None,
            "full_name": log.employee.full_name if log.employee else None,
            "dept_name": log.employee.department.name if log.employee and log.employee.department else None,
            "station_id": log.station_id,
            "station_name": log.station.name if log.station else None,
            "timestamp": log.timestamp,
            "confidence_score": log.confidence_score,
            "snapshot_url": f"/api/v1/attendance/{log.id}/snapshot" if log.snapshot_path else None,
        }
        for log in logs
    ]


@router.get("/{log_id}/snapshot")
async def get_attendance_snapshot(
    log_id: int,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    """ดึง face snapshot ที่บันทึกตอน scan (auth required — เป็น biometric evidence)"""
    result = await db.execute(
        select(AttendanceLog).where(AttendanceLog.id == log_id)
    )
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(404, "Attendance record not found")
    if not log.snapshot_path:
        raise HTTPException(404, "No snapshot for this record")

    path = Path(log.snapshot_path)
    if not path.exists():
        raise HTTPException(404, "Snapshot file not found on disk")

    return FileResponse(path, media_type="image/jpeg")


@router.get("/summary")
async def attendance_summary(
    month: str = Query(default=None, description="YYYY-MM format, defaults to current month"),
    dept_id: int = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    """
    Monthly attendance summary:
    - total records in the month
    - unique employees who attended
    - by_day: daily counts + unique employees per day
    - by_department: breakdown per department
    """
    # Resolve month
    today = datetime.now(timezone.utc).date()
    if month:
        try:
            year, mon = int(month[:4]), int(month[5:7])
        except (ValueError, IndexError):
            year, mon = today.year, today.month
    else:
        year, mon = today.year, today.month

    _, last_day = calendar.monthrange(year, mon)
    start = datetime(year, mon, 1, tzinfo=timezone.utc)
    end   = datetime(year, mon, last_day, 23, 59, 59, tzinfo=timezone.utc)

    # Base query
    base_q = (
        select(AttendanceLog)
        .options(selectinload(AttendanceLog.employee).selectinload(Employee.department))
        .where(AttendanceLog.timestamp.between(start, end))
    )
    if dept_id:
        base_q = base_q.join(AttendanceLog.employee).where(Employee.dept_id == dept_id)

    result = await db.execute(base_q)
    logs = result.scalars().all()

    # ── by_day aggregation ────────────────────────────────────────────────────
    day_map: dict[str, dict] = {}
    for log in logs:
        d = log.timestamp.strftime("%Y-%m-%d")
        if d not in day_map:
            day_map[d] = {"date": d, "count": 0, "unique_employees": set()}
        day_map[d]["count"] += 1
        day_map[d]["unique_employees"].add(str(log.employee_id))

    by_day = sorted([
        {"date": d, "count": v["count"], "unique_employees": len(v["unique_employees"])}
        for d, v in day_map.items()
    ], key=lambda x: x["date"])

    # Fill missing days with 0
    full_days = []
    for day_num in range(1, last_day + 1):
        d = f"{year:04d}-{mon:02d}-{day_num:02d}"
        existing = next((x for x in by_day if x["date"] == d), None)
        full_days.append(existing or {"date": d, "count": 0, "unique_employees": 0})

    # ── by_department aggregation ─────────────────────────────────────────────
    dept_map: dict[int, dict] = {}
    for log in logs:
        dept = log.employee.department if log.employee else None
        did  = dept.id   if dept else 0
        name = dept.name if dept else "Unknown"
        if did not in dept_map:
            dept_map[did] = {"dept_id": did, "dept_name": name, "count": 0, "unique_employees": set()}
        dept_map[did]["count"] += 1
        dept_map[did]["unique_employees"].add(str(log.employee_id))

    by_department = sorted([
        {"dept_id": d["dept_id"], "dept_name": d["dept_name"],
         "count": d["count"], "unique_employees": len(d["unique_employees"])}
        for d in dept_map.values()
    ], key=lambda x: -x["count"])

    # ── totals ────────────────────────────────────────────────────────────────
    all_employees = {str(log.employee_id) for log in logs}

    return {
        "month": f"{year:04d}-{mon:02d}",
        "total_records": len(logs),
        "unique_employees": len(all_employees),
        "by_day": full_days,
        "by_department": by_department,
    }
