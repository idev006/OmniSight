from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from app.db.postgres import get_db
from app.models.orm import Employee, FaceTemplate
from app.models.schemas import EmployeeCreate, EmployeeOut, EmployeePage
from app.core.security import require_hr, CurrentUser
import uuid

router = APIRouter()


@router.get("", response_model=list[EmployeeOut])
async def list_employees(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    result = await db.execute(
        select(Employee).options(selectinload(Employee.face_templates)).order_by(Employee.emp_code)
    )
    employees = result.scalars().all()
    return [_enrich(e) for e in employees]


@router.get("/page", response_model=EmployeePage)
async def list_employees_page(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=200),
    search: str = Query(default=""),
    dept_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    filters = []
    q = search.strip()
    if q:
        like = f"%{q}%"
        filters.append(or_(Employee.emp_code.ilike(like), Employee.full_name.ilike(like)))
    if dept_id is not None:
        filters.append(Employee.dept_id == dept_id)

    total_stmt = select(func.count()).select_from(Employee)
    if filters:
        total_stmt = total_stmt.where(*filters)
    total = (await db.execute(total_stmt)).scalar_one()

    enrollment_counts = (
        select(
            FaceTemplate.employee_id.label("employee_id"),
            func.count(FaceTemplate.id).label("enrollment_count"),
        )
        .group_by(FaceTemplate.employee_id)
        .subquery()
    )

    stmt = (
        select(Employee, func.coalesce(enrollment_counts.c.enrollment_count, 0).label("enrollment_count"))
        .outerjoin(enrollment_counts, enrollment_counts.c.employee_id == Employee.id)
        .order_by(Employee.emp_code)
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    if filters:
        stmt = stmt.where(*filters)

    rows = (await db.execute(stmt)).all()
    items = [_enrich_with_count(emp, count) for emp, count in rows]
    return EmployeePage(items=items, total=total, page=page, page_size=page_size)


@router.post("", response_model=EmployeeOut, status_code=201)
async def create_employee(
    body: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    emp = Employee(**body.model_dump())
    db.add(emp)
    await db.commit()
    await db.refresh(emp, ["face_templates"])
    return _enrich(emp)


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    result = await db.execute(
        select(Employee).options(selectinload(Employee.face_templates)).where(Employee.id == employee_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, "Employee not found")
    return _enrich(emp)


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(
    employee_id: uuid.UUID,
    body: EmployeeCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    result = await db.execute(
        select(Employee).options(selectinload(Employee.face_templates)).where(Employee.id == employee_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, "Employee not found")
    for k, v in body.model_dump(exclude_unset=True).items():
        setattr(emp, k, v)
    await db.commit()
    await db.refresh(emp, ["face_templates"])
    return _enrich(emp)


def _enrich(emp: Employee) -> EmployeeOut:
    count = len(emp.face_templates)
    return _enrich_with_count(emp, count)


def _enrich_with_count(emp: Employee, count: int) -> EmployeeOut:
    return EmployeeOut(
        id=emp.id,
        emp_code=emp.emp_code,
        full_name=emp.full_name,
        dept_id=emp.dept_id,
        shift_id=emp.shift_id,
        is_active=emp.is_active,
        enrollment_count=count,
        is_enrollment_complete=count >= 6,
    )
