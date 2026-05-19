from fastapi import APIRouter, Depends, Query, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, cast, Date
from sqlalchemy.orm import selectinload
from app.db.postgres import get_db
from app.models.orm import AttendanceLog, Employee, Station, Department, Shift
from app.core.security import require_hr, CurrentUser
from app.db.redis import redis as _redis
from datetime import date, datetime, timezone, timedelta
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


@router.get("/kpi")
async def attendance_kpi(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    """
    Dashboard KPI:
    - today: present/late/absent counts + percentages
    - weekly: last 7 days check-in counts (for trend chart)
    - by_dept: today's check-ins grouped by department
    """
    today = datetime.now(timezone.utc).date()

    # ── Today's unique check-ins ──────────────────────────────────────────────
    today_logs = await db.execute(
        select(
            AttendanceLog.employee_id,
            func.min(AttendanceLog.check_in_time).label("first_checkin"),
        )
        .where(cast(AttendanceLog.check_in_time, Date) == today)
        .group_by(AttendanceLog.employee_id)
    )
    today_checkins = {row.employee_id: row.first_checkin for row in today_logs}

    # ── All employees with shift assigned (for ABSENT calculation) ───────────
    emp_rows = await db.execute(
        select(Employee, Shift, Department.name.label("dept_name"))
        .join(Shift, Shift.id == Employee.shift_id)
        .join(Department, Department.id == Employee.dept_id, isouter=True)
        .where(Employee.is_active == True)
    )
    employees_with_shift = emp_rows.all()

    # ── Late threshold from Redis ─────────────────────────────────────────────
    late_val = await _redis.get("setting:late_threshold_minutes")
    late_threshold = int(late_val) if late_val else 15

    present = late = absent = 0
    for emp, shift, dept_name in employees_with_shift:
        checkin = today_checkins.get(emp.id)
        if checkin is None:
            absent += 1
        else:
            shift_start = datetime.combine(today, shift.start_time, tzinfo=timezone.utc)
            if checkin <= shift_start + timedelta(minutes=late_threshold):
                present += 1
            else:
                late += 1

    total_with_shift = len(employees_with_shift)
    def pct(n): return round(n / total_with_shift * 100, 1) if total_with_shift else 0.0

    # ── Weekly trend (last 7 days unique check-ins per day) ──────────────────
    weekly = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        res = await db.execute(
            select(func.count(func.distinct(AttendanceLog.employee_id)))
            .where(cast(AttendanceLog.check_in_time, Date) == d)
        )
        weekly.append({"date": d.isoformat(), "count": res.scalar() or 0})

    # ── By department (today) ─────────────────────────────────────────────────
    dept_rows = await db.execute(
        select(Department.name, func.count(func.distinct(AttendanceLog.employee_id)).label("count"))
        .join(Employee, Employee.dept_id == Department.id)
        .join(AttendanceLog, AttendanceLog.employee_id == Employee.id)
        .where(cast(AttendanceLog.check_in_time, Date) == today)
        .group_by(Department.name)
        .order_by(func.count(func.distinct(AttendanceLog.employee_id)).desc())
    )
    by_dept = [{"dept": r.name, "count": r.count} for r in dept_rows]

    return {
        "date": today.isoformat(),
        "today": {
            "total":   total_with_shift,
            "present": present, "present_pct": pct(present),
            "late":    late,    "late_pct":    pct(late),
            "absent":  absent,  "absent_pct":  pct(absent),
        },
        "weekly":  weekly,
        "by_dept": by_dept,
    }


@router.get("/daily-report")
async def daily_attendance_report(
    report_date: date = Query(default=None, alias="date"),
    dept_id: int = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    """
    รายงานสถานะรายวัน: PRESENT / LATE / ABSENT สำหรับพนักงานที่มี Shift กำหนดไว้

    - PRESENT : มี attendance log ก่อนหรือภายใน late_threshold_minutes หลัง shift.start_time
    - LATE    : log แรกมาหลัง shift.start_time + late_threshold_minutes
    - ABSENT  : ไม่มี log เลยในวันนั้น
    """
    target_date = report_date or datetime.now(timezone.utc).date()

    # อ่าน late threshold จาก Redis (live setting)
    late_threshold = 15
    try:
        val = await _redis.get("setting:late_threshold_minutes")
        if val:
            late_threshold = max(0, int(val))
    except Exception:
        pass

    # ── ดึงพนักงานทั้งหมดที่มี shift กำหนดไว้ ─────────────────────────────────
    emp_q = (
        select(Employee)
        .options(
            selectinload(Employee.department),
            selectinload(Employee.shift),
        )
        .where(Employee.is_active == True, Employee.shift_id.isnot(None))
    )
    if dept_id:
        emp_q = emp_q.where(Employee.dept_id == dept_id)

    emp_result = await db.execute(emp_q)
    employees = emp_result.scalars().all()

    if not employees:
        return {"date": str(target_date), "late_threshold_minutes": late_threshold, "records": []}

    # ── ดึง attendance logs ของวันนั้น สำหรับพนักงานที่เลือก ───────────────────
    emp_ids = [e.id for e in employees]
    day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=timezone.utc)
    day_end   = day_start + timedelta(days=1)

    logs_q = (
        select(AttendanceLog)
        .where(
            AttendanceLog.employee_id.in_(emp_ids),
            AttendanceLog.timestamp >= day_start,
            AttendanceLog.timestamp < day_end,
        )
        .order_by(AttendanceLog.timestamp.asc())
    )
    logs_result = await db.execute(logs_q)
    logs = logs_result.scalars().all()

    # หา first check-in per employee
    first_checkin: dict = {}
    for log in logs:
        eid = str(log.employee_id)
        if eid not in first_checkin:
            first_checkin[eid] = log

    # ── คำนวณสถานะ ─────────────────────────────────────────────────────────────
    records = []
    for emp in employees:
        eid = str(emp.id)
        shift = emp.shift
        first_log = first_checkin.get(eid)

        if first_log is None:
            status = "ABSENT"
            check_in_time = None
            minutes_late = None
        else:
            check_in_time = first_log.timestamp
            # เปรียบเทียบเวลา check-in (UTC) กับ shift.start_time
            shift_start_dt = datetime(
                target_date.year, target_date.month, target_date.day,
                shift.start_time.hour, shift.start_time.minute,
                tzinfo=timezone.utc,
            )
            delta_seconds = (check_in_time - shift_start_dt).total_seconds()
            minutes_late = max(0, int(delta_seconds // 60))

            if delta_seconds <= late_threshold * 60:
                status = "PRESENT"
            else:
                status = "LATE"

        records.append({
            "employee_id":  str(emp.id),
            "emp_code":     emp.emp_code,
            "full_name":    emp.full_name,
            "dept_name":    emp.department.name if emp.department else None,
            "shift_name":   shift.name,
            "shift_start":  shift.start_time.strftime("%H:%M"),
            "shift_end":    shift.end_time.strftime("%H:%M"),
            "check_in_time": check_in_time.isoformat() if check_in_time else None,
            "minutes_late": minutes_late,
            "status":       status,
        })

    # เรียงลำดับ: ABSENT ก่อน, LATE, PRESENT
    order = {"ABSENT": 0, "LATE": 1, "PRESENT": 2}
    records.sort(key=lambda r: (order[r["status"]], r["full_name"]))

    summary = {
        "total": len(records),
        "present": sum(1 for r in records if r["status"] == "PRESENT"),
        "late":    sum(1 for r in records if r["status"] == "LATE"),
        "absent":  sum(1 for r in records if r["status"] == "ABSENT"),
    }

    return {
        "date": str(target_date),
        "late_threshold_minutes": late_threshold,
        "summary": summary,
        "records": records,
    }


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
