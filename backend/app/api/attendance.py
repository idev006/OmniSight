import calendar
import io
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy import Date, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.security import CurrentUser, require_hr
from app.db.postgres import get_db
from app.db.redis import redis as _redis
from app.models.orm import AttendanceLog, Department, Employee, Shift

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
        start = datetime(date.year, date.month, date.day, tzinfo=UTC)
        end = datetime(date.year, date.month, date.day, 23, 59, 59, tzinfo=UTC)
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
    today = datetime.now(UTC).date()

    # ── Today's unique check-ins ──────────────────────────────────────────────
    today_logs = await db.execute(
        select(
            AttendanceLog.employee_id,
            func.min(AttendanceLog.timestamp).label("first_checkin"),
        )
        .where(cast(AttendanceLog.timestamp, Date) == today)
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
    for emp, shift, _dept_name in employees_with_shift:
        checkin = today_checkins.get(emp.id)
        if checkin is None:
            absent += 1
        else:
            shift_start = datetime.combine(today, shift.start_time, tzinfo=UTC)
            if checkin <= shift_start + timedelta(minutes=late_threshold):
                present += 1
            else:
                late += 1

    total_with_shift = len(employees_with_shift)

    def pct(n):
        return round(n / total_with_shift * 100, 1) if total_with_shift else 0.0

    # ── Weekly trend (last 7 days unique check-ins per day) ──────────────────
    weekly = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        res = await db.execute(
            select(func.count(func.distinct(AttendanceLog.employee_id))).where(cast(AttendanceLog.timestamp, Date) == d)
        )
        weekly.append({"date": d.isoformat(), "count": res.scalar() or 0})

    # ── By department (today) ─────────────────────────────────────────────────
    dept_rows = await db.execute(
        select(Department.name, func.count(func.distinct(AttendanceLog.employee_id)).label("count"))
        .join(Employee, Employee.dept_id == Department.id)
        .join(AttendanceLog, AttendanceLog.employee_id == Employee.id)
        .where(cast(AttendanceLog.timestamp, Date) == today)
        .group_by(Department.name)
        .order_by(func.count(func.distinct(AttendanceLog.employee_id)).desc())
    )
    by_dept = [{"dept": r.name, "count": r.count} for r in dept_rows]

    return {
        "date": today.isoformat(),
        "today": {
            "total": total_with_shift,
            "present": present,
            "present_pct": pct(present),
            "late": late,
            "late_pct": pct(late),
            "absent": absent,
            "absent_pct": pct(absent),
        },
        "weekly": weekly,
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
    target_date = report_date or datetime.now(UTC).date()

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
    day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

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
                target_date.year,
                target_date.month,
                target_date.day,
                shift.start_time.hour,
                shift.start_time.minute,
                tzinfo=UTC,
            )
            delta_seconds = (check_in_time - shift_start_dt).total_seconds()
            minutes_late = max(0, int(delta_seconds // 60))

            if delta_seconds <= late_threshold * 60:
                status = "PRESENT"
            else:
                status = "LATE"

        records.append(
            {
                "employee_id": str(emp.id),
                "emp_code": emp.emp_code,
                "full_name": emp.full_name,
                "dept_name": emp.department.name if emp.department else None,
                "shift_name": shift.name,
                "shift_start": shift.start_time.strftime("%H:%M"),
                "shift_end": shift.end_time.strftime("%H:%M"),
                "check_in_time": check_in_time.isoformat() if check_in_time else None,
                "minutes_late": minutes_late,
                "status": status,
            }
        )

    # เรียงลำดับ: ABSENT ก่อน, LATE, PRESENT
    order = {"ABSENT": 0, "LATE": 1, "PRESENT": 2}
    records.sort(key=lambda r: (order[r["status"]], r["full_name"]))

    summary = {
        "total": len(records),
        "present": sum(1 for r in records if r["status"] == "PRESENT"),
        "late": sum(1 for r in records if r["status"] == "LATE"),
        "absent": sum(1 for r in records if r["status"] == "ABSENT"),
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
    result = await db.execute(select(AttendanceLog).where(AttendanceLog.id == log_id))
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
    today = datetime.now(UTC).date()
    if month:
        try:
            year, mon = int(month[:4]), int(month[5:7])
        except (ValueError, IndexError):
            year, mon = today.year, today.month
    else:
        year, mon = today.year, today.month

    _, last_day = calendar.monthrange(year, mon)
    start = datetime(year, mon, 1, tzinfo=UTC)
    end = datetime(year, mon, last_day, 23, 59, 59, tzinfo=UTC)

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

    by_day = sorted(
        [{"date": d, "count": v["count"], "unique_employees": len(v["unique_employees"])} for d, v in day_map.items()],
        key=lambda x: x["date"],
    )

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
        did = dept.id if dept else 0
        name = dept.name if dept else "Unknown"
        if did not in dept_map:
            dept_map[did] = {"dept_id": did, "dept_name": name, "count": 0, "unique_employees": set()}
        dept_map[did]["count"] += 1
        dept_map[did]["unique_employees"].add(str(log.employee_id))

    by_department = sorted(
        [
            {
                "dept_id": d["dept_id"],
                "dept_name": d["dept_name"],
                "count": d["count"],
                "unique_employees": len(d["unique_employees"]),
            }
            for d in dept_map.values()
        ],
        key=lambda x: -x["count"],
    )

    # ── totals ────────────────────────────────────────────────────────────────
    all_employees = {str(log.employee_id) for log in logs}

    return {
        "month": f"{year:04d}-{mon:02d}",
        "total_records": len(logs),
        "unique_employees": len(all_employees),
        "by_day": full_days,
        "by_department": by_department,
    }


# ── PDF Export ────────────────────────────────────────────────────────────────


def _build_daily_report_pdf(
    target_date: date,
    late_threshold: int,
    summary: dict,
    records: list[dict],
) -> bytes:
    """
    Build the daily attendance report as a PDF byte string using ReportLab.

    Thai text support: Leelawadee TTF (bundled in app/assets/fonts/).
    Falls back to Helvetica if font missing (Thai chars will render as boxes).

    Layout:
    - Header: title + date + late threshold
    - Summary box: total / present / late / absent
    - Table: emp_code | full_name | dept | shift | check_in_time | status
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"reportlab not installed: {e}") from e

    from app.core.pdf_utils import BODY_SIZE, HEADER_SIZE, TITLE_SIZE, get_font, get_font_bold

    font = get_font()
    font_bold = get_font_bold()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=landscape(A4),
        leftMargin=1.5 * cm,
        rightMargin=1.5 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        "OmniTitle",
        parent=styles["Title"],
        fontName=font_bold,
        fontSize=TITLE_SIZE,
        leading=TITLE_SIZE * 1.4,
    )
    body_style = ParagraphStyle(
        "OmniBody",
        parent=styles["Normal"],
        fontName=font,
        fontSize=BODY_SIZE,
    )

    # ── Status colour map ─────────────────────────────────────────────────────
    STATUS_COLOR = {
        "PRESENT": colors.HexColor("#22c55e"),  # green-500
        "LATE": colors.HexColor("#f59e0b"),  # amber-500
        "ABSENT": colors.HexColor("#ef4444"),  # red-500
    }

    story = []

    # ── Title ─────────────────────────────────────────────────────────────────
    story.append(
        Paragraph(
            f"OmniSight — Daily Attendance Report<br/>"
            f"<font size='{HEADER_SIZE}'>Date: {target_date}"
            f"  |  Late threshold: {late_threshold} min</font>",
            title_style,
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    # ── Summary row ───────────────────────────────────────────────────────────
    summary_data = [
        ["Total", "Present", "Late", "Absent"],
        [
            str(summary["total"]),
            str(summary["present"]),
            str(summary["late"]),
            str(summary["absent"]),
        ],
    ]
    summary_table = Table(summary_data, colWidths=[4 * cm] * 4)
    summary_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("FONTNAME", (0, 0), (-1, 0), font_bold),
                ("FONTSIZE", (0, 0), (-1, -1), HEADER_SIZE),
                ("ALIGN", (0, 0), (-1, -1), "CENTER"),
                ("FONTNAME", (0, 1), (-1, -1), font),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f0f4ff"), colors.white]),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(summary_table)
    story.append(Spacer(1, 0.6 * cm))

    # ── Detail table ──────────────────────────────────────────────────────────
    headers = ["#", "Emp Code", "Name", "Department", "Shift", "Check-in", "Status"]
    col_widths = [1 * cm, 3 * cm, 6.5 * cm, 5.5 * cm, 3.5 * cm, 3.5 * cm, 3 * cm]

    table_data = [headers]
    for i, r in enumerate(records, start=1):
        check_in = r["check_in_time"]
        if check_in:
            try:
                check_in = datetime.fromisoformat(check_in).strftime("%H:%M:%S")
            except ValueError:
                pass
        table_data.append(
            [
                str(i),
                r["emp_code"] or "",
                r["full_name"] or "",
                r["dept_name"] or "—",
                f"{r['shift_start']}–{r['shift_end']}",
                check_in or "—",
                r["status"],
            ]
        )

    detail_table = Table(table_data, colWidths=col_widths, repeatRows=1)

    base_style = [
        # Header row
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e3a5f")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), font_bold),
        ("FONTSIZE", (0, 0), (-1, 0), HEADER_SIZE),
        # Body rows
        ("FONTNAME", (0, 1), (-1, -1), font),
        ("FONTSIZE", (0, 1), (-1, -1), BODY_SIZE),
        # Alignment
        ("ALIGN", (0, 0), (0, -1), "CENTER"),  # row number
        ("ALIGN", (5, 0), (5, -1), "CENTER"),  # check-in
        ("ALIGN", (6, 0), (6, -1), "CENTER"),  # status
        # Grid & padding
        ("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#cbd5e1")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ]

    # Per-row status colouring
    for row_idx, r in enumerate(records, start=1):
        status_col = STATUS_COLOR.get(r["status"], colors.grey)
        base_style.append(("TEXTCOLOR", (6, row_idx), (6, row_idx), status_col))
        base_style.append(("FONTNAME", (6, row_idx), (6, row_idx), font_bold))

    detail_table.setStyle(TableStyle(base_style))
    story.append(detail_table)

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 0.4 * cm))
    story.append(
        Paragraph(
            f"Generated by OmniSight on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            body_style,
        )
    )

    doc.build(story)
    return buf.getvalue()


@router.get("/daily-report/pdf")
async def daily_attendance_report_pdf(
    report_date: date = Query(default=None, alias="date"),
    dept_id: int = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    """
    Export the daily attendance report as a downloadable PDF.

    Reuses the same data logic as GET /daily-report (JSON).
    Returns a PDF with:
    - Header (title, date, late threshold)
    - Summary box (total / present / late / absent)
    - Per-employee detail table (sorted: ABSENT → LATE → PRESENT)

    Requires HR or ADMIN role.
    """
    target_date = report_date or datetime.now(UTC).date()

    # Read late threshold from Redis
    late_threshold = 15
    try:
        val = await _redis.get("setting:late_threshold_minutes")
        if val:
            late_threshold = max(0, int(val))
    except Exception:
        pass

    # Fetch employees with shift
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
        # Return an empty-record PDF rather than 404
        records = []
        summary = {"total": 0, "present": 0, "late": 0, "absent": 0}
        pdf_bytes = _build_daily_report_pdf(target_date, late_threshold, summary, records)
        filename = f"attendance_{target_date}.pdf"
        return StreamingResponse(
            io.BytesIO(pdf_bytes),
            media_type="application/pdf",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )

    # Fetch attendance logs for target date
    emp_ids = [e.id for e in employees]
    day_start = datetime(target_date.year, target_date.month, target_date.day, tzinfo=UTC)
    day_end = day_start + timedelta(days=1)

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

    # First check-in per employee
    first_checkin: dict = {}
    for log in logs:
        eid = str(log.employee_id)
        if eid not in first_checkin:
            first_checkin[eid] = log

    # Build records
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
            shift_start_dt = datetime(
                target_date.year,
                target_date.month,
                target_date.day,
                shift.start_time.hour,
                shift.start_time.minute,
                tzinfo=UTC,
            )
            delta_seconds = (check_in_time - shift_start_dt).total_seconds()
            minutes_late = max(0, int(delta_seconds // 60))
            status = "PRESENT" if delta_seconds <= late_threshold * 60 else "LATE"

        records.append(
            {
                "employee_id": str(emp.id),
                "emp_code": emp.emp_code,
                "full_name": emp.full_name,
                "dept_name": emp.department.name if emp.department else None,
                "shift_name": shift.name,
                "shift_start": shift.start_time.strftime("%H:%M"),
                "shift_end": shift.end_time.strftime("%H:%M"),
                "check_in_time": check_in_time.isoformat() if check_in_time else None,
                "minutes_late": minutes_late,
                "status": status,
            }
        )

    order = {"ABSENT": 0, "LATE": 1, "PRESENT": 2}
    records.sort(key=lambda r: (order[r["status"]], r["full_name"]))

    summary = {
        "total": len(records),
        "present": sum(1 for r in records if r["status"] == "PRESENT"),
        "late": sum(1 for r in records if r["status"] == "LATE"),
        "absent": sum(1 for r in records if r["status"] == "ABSENT"),
    }

    pdf_bytes = _build_daily_report_pdf(target_date, late_threshold, summary, records)
    filename = f"attendance_{target_date}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


# ── Monthly PDF ───────────────────────────────────────────────────────────────


def _build_monthly_report_pdf(
    year: int,
    mon: int,
    total_records: int,
    unique_employees: int,
    by_day: list[dict],
    by_department: list[dict],
) -> bytes:
    """
    Build the monthly attendance summary as a PDF byte string.

    Layout (portrait A4):
    - Title + month
    - Summary stats: total records / unique employees
    - Daily breakdown table: date | count | unique employees
    - Department breakdown table: dept | count | unique employees
    """
    try:
        from reportlab.lib import colors
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
        from reportlab.lib.units import cm
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"reportlab not installed: {e}") from e

    from app.core.pdf_utils import BODY_SIZE, HEADER_SIZE, TITLE_SIZE, get_font, get_font_bold

    font = get_font()
    font_bold = get_font_bold()

    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "MT", parent=styles["Title"], fontName=font_bold, fontSize=TITLE_SIZE, leading=TITLE_SIZE * 1.4
    )
    section_style = ParagraphStyle("MS", parent=styles["Heading2"], fontName=font_bold, fontSize=HEADER_SIZE + 1)
    body_style = ParagraphStyle("MB", parent=styles["Normal"], fontName=font, fontSize=BODY_SIZE)

    _HDR = colors.HexColor("#1e3a5f")
    _ALT = colors.HexColor("#f8fafc")
    _GRID = colors.HexColor("#cbd5e1")

    def _tbl_style(n_header_rows: int = 1) -> TableStyle:
        return TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, n_header_rows - 1), _HDR),
                ("TEXTCOLOR", (0, 0), (-1, n_header_rows - 1), colors.white),
                ("FONTNAME", (0, 0), (-1, n_header_rows - 1), font_bold),
                ("FONTSIZE", (0, 0), (-1, n_header_rows - 1), HEADER_SIZE),
                ("FONTNAME", (0, n_header_rows), (-1, -1), font),
                ("FONTSIZE", (0, n_header_rows), (-1, -1), BODY_SIZE),
                ("ALIGN", (1, 0), (-1, -1), "CENTER"),
                ("ROWBACKGROUNDS", (0, n_header_rows), (-1, -1), [colors.white, _ALT]),
                ("GRID", (0, 0), (-1, -1), 0.3, _GRID),
                ("TOPPADDING", (0, 0), (-1, -1), 4),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ]
        )

    story = []

    # ── Title ─────────────────────────────────────────────────────────────────
    month_name = f"{year:04d}-{mon:02d}"
    story.append(
        Paragraph(
            f"OmniSight — Monthly Attendance Summary<br/><font size='{HEADER_SIZE}'>{month_name}</font>", title_style
        )
    )
    story.append(Spacer(1, 0.4 * cm))

    # ── Totals summary ────────────────────────────────────────────────────────
    totals_data = [
        ["Total Check-in Records", "Unique Employees"],
        [str(total_records), str(unique_employees)],
    ]
    totals_tbl = Table(totals_data, colWidths=[8 * cm, 8 * cm])
    totals_tbl.setStyle(_tbl_style())
    story.append(totals_tbl)
    story.append(Spacer(1, 0.7 * cm))

    # ── Daily breakdown ───────────────────────────────────────────────────────
    story.append(Paragraph("Daily Breakdown", section_style))
    story.append(Spacer(1, 0.2 * cm))

    day_headers = ["Date", "Check-in Records", "Unique Employees"]
    day_data = [day_headers] + [[d["date"], str(d["count"]), str(d["unique_employees"])] for d in by_day]
    day_tbl = Table(day_data, colWidths=[5 * cm, 5.5 * cm, 5.5 * cm], repeatRows=1)
    day_tbl.setStyle(_tbl_style())
    story.append(day_tbl)
    story.append(Spacer(1, 0.7 * cm))

    # ── Department breakdown ──────────────────────────────────────────────────
    if by_department:
        story.append(Paragraph("By Department", section_style))
        story.append(Spacer(1, 0.2 * cm))

        dept_headers = ["Department", "Check-in Records", "Unique Employees"]
        dept_data = [dept_headers] + [
            [d["dept_name"], str(d["count"]), str(d["unique_employees"])] for d in by_department
        ]
        dept_tbl = Table(dept_data, colWidths=[7 * cm, 5 * cm, 5 * cm], repeatRows=1)
        dept_tbl.setStyle(_tbl_style())
        story.append(dept_tbl)
        story.append(Spacer(1, 0.4 * cm))

    # ── Footer ────────────────────────────────────────────────────────────────
    story.append(
        Paragraph(
            f"Generated by OmniSight on {datetime.now(UTC).strftime('%Y-%m-%d %H:%M UTC')}",
            body_style,
        )
    )

    doc.build(story)
    return buf.getvalue()


@router.get("/summary/pdf")
async def attendance_summary_pdf(
    month: str = Query(default=None, description="YYYY-MM format, defaults to current month"),
    dept_id: int = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    """
    Export the monthly attendance summary as a downloadable PDF.

    Mirrors GET /summary (JSON) — same data, PDF output.
    Returns portrait A4 PDF with:
    - Total records + unique employees
    - Daily breakdown table (all days in month, zero-filled)
    - Department breakdown table

    Requires HR or ADMIN role.
    """
    today = datetime.now(UTC).date()
    if month:
        try:
            year, mon = int(month[:4]), int(month[5:7])
        except (ValueError, IndexError):
            year, mon = today.year, today.month
    else:
        year, mon = today.year, today.month

    _, last_day = calendar.monthrange(year, mon)
    start = datetime(year, mon, 1, tzinfo=UTC)
    end = datetime(year, mon, last_day, 23, 59, 59, tzinfo=UTC)

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

    by_day_raw = [
        {"date": d, "count": v["count"], "unique_employees": len(v["unique_employees"])} for d, v in day_map.items()
    ]
    # Fill all days including zeros
    by_day = []
    for day_num in range(1, last_day + 1):
        d = f"{year:04d}-{mon:02d}-{day_num:02d}"
        existing = next((x for x in by_day_raw if x["date"] == d), None)
        by_day.append(existing or {"date": d, "count": 0, "unique_employees": 0})

    # ── by_department aggregation ─────────────────────────────────────────────
    dept_map: dict[int, dict] = {}
    for log in logs:
        dept = log.employee.department if log.employee else None
        did = dept.id if dept else 0
        name = dept.name if dept else "Unknown"
        if did not in dept_map:
            dept_map[did] = {"dept_name": name, "count": 0, "unique_employees": set()}
        dept_map[did]["count"] += 1
        dept_map[did]["unique_employees"].add(str(log.employee_id))

    by_department = sorted(
        [
            {"dept_name": d["dept_name"], "count": d["count"], "unique_employees": len(d["unique_employees"])}
            for d in dept_map.values()
        ],
        key=lambda x: -x["count"],
    )

    all_employees = {str(log.employee_id) for log in logs}

    pdf_bytes = _build_monthly_report_pdf(
        year=year,
        mon=mon,
        total_records=len(logs),
        unique_employees=len(all_employees),
        by_day=by_day,
        by_department=by_department,
    )
    filename = f"attendance_monthly_{year:04d}-{mon:02d}.pdf"
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )
