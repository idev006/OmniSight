from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.postgres import get_db
from app.models.orm import AttendanceLog, Employee, Station, Department
from datetime import date, datetime, timezone

router = APIRouter()


@router.get("")
async def list_attendance(
    date: date = Query(default=None),
    dept_id: int = Query(default=None),
    limit: int = Query(default=100, le=1000),
    db: AsyncSession = Depends(get_db),
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
        }
        for log in logs
    ]
