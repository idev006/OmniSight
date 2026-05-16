from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from sqlalchemy.orm import selectinload
from app.db.postgres import get_db
from app.models.orm import Employee, FaceTemplate
from app.models.schemas import EmployeeCreate, EmployeeOut
import uuid

router = APIRouter()


@router.get("", response_model=list[EmployeeOut])
async def list_employees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.face_templates))
        .order_by(Employee.emp_code)
    )
    employees = result.scalars().all()
    return [_enrich(e) for e in employees]


@router.post("", response_model=EmployeeOut, status_code=201)
async def create_employee(body: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    emp = Employee(**body.model_dump())
    db.add(emp)
    await db.commit()
    await db.refresh(emp, ["face_templates"])
    return _enrich(emp)


@router.get("/{employee_id}", response_model=EmployeeOut)
async def get_employee(employee_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.face_templates))
        .where(Employee.id == employee_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, "Employee not found")
    return _enrich(emp)


@router.patch("/{employee_id}", response_model=EmployeeOut)
async def update_employee(employee_id: uuid.UUID, body: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(Employee)
        .options(selectinload(Employee.face_templates))
        .where(Employee.id == employee_id)
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
