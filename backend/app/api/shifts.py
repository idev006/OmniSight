from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.postgres import get_db
from app.models.orm import Shift
from app.models.schemas import ShiftCreate, ShiftOut

router = APIRouter()


@router.get("", response_model=list[ShiftOut])
async def list_shifts(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Shift).order_by(Shift.id))
    return result.scalars().all()


@router.post("", response_model=ShiftOut, status_code=201)
async def create_shift(body: ShiftCreate, db: AsyncSession = Depends(get_db)):
    shift = Shift(**body.model_dump())
    db.add(shift)
    await db.commit()
    await db.refresh(shift)
    return shift


@router.delete("/{shift_id}", status_code=204)
async def delete_shift(shift_id: int, db: AsyncSession = Depends(get_db)):
    shift = await db.get(Shift, shift_id)
    if not shift:
        raise HTTPException(404, "Shift not found")
    await db.delete(shift)
    await db.commit()
