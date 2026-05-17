from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.postgres import get_db
from app.models.orm import Department
from app.models.schemas import DepartmentCreate, DepartmentOut
from app.core.security import require_admin, require_hr, CurrentUser

router = APIRouter()


@router.get("", response_model=list[DepartmentOut])
async def list_departments(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    result = await db.execute(select(Department).order_by(Department.id))
    return result.scalars().all()


@router.post("", response_model=DepartmentOut, status_code=201)
async def create_department(
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    dept = Department(name=body.name)
    db.add(dept)
    await db.commit()
    await db.refresh(dept)
    return dept


@router.put("/{dept_id}", response_model=DepartmentOut)
async def update_department(
    dept_id: int,
    body: DepartmentCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    dept = await db.get(Department, dept_id)
    if not dept:
        raise HTTPException(404, "Department not found")
    dept.name = body.name
    await db.commit()
    await db.refresh(dept)
    return dept


@router.delete("/{dept_id}", status_code=204)
async def delete_department(
    dept_id: int,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    dept = await db.get(Department, dept_id)
    if not dept:
        raise HTTPException(404, "Department not found")
    await db.delete(dept)
    await db.commit()
