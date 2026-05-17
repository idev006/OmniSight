"""
User Management API — ADMIN only
CRUD for users + station assignments
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
import uuid

from app.core.security import require_admin, CurrentUser, hash_password
from app.db.postgres import get_db
from app.models.orm import User, UserStation, Station
from app.models.schemas import (
    UserCreate, UserOut, UserUpdate, UserStationUpdate
)

def _out(user) -> UserOut:
    return UserOut.from_orm_user(user)

router = APIRouter()


@router.get("", response_model=list[UserOut])
async def list_users(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    result = await db.execute(
        select(User).options(selectinload(User.user_stations)).order_by(User.username)
    )
    return [_out(u) for u in result.scalars().all()]


@router.post("", response_model=UserOut, status_code=201)
async def create_user(
    body: UserCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    # Check duplicate username
    existing = await db.execute(select(User).where(User.username == body.username))
    if existing.scalar_one_or_none():
        raise HTTPException(400, f"Username '{body.username}' already exists")

    user = User(
        username=body.username,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        role=body.role,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user, ["user_stations"])
    return _out(user)


@router.get("/{user_id}", response_model=UserOut)
async def get_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_stations))
        .where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    return _out(user)


@router.put("/{user_id}", response_model=UserOut)
async def update_user(
    user_id: str,
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    result = await db.execute(
        select(User).options(selectinload(User.user_stations))
        .where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    if body.full_name is not None:
        user.full_name = body.full_name
    if body.role is not None:
        user.role = body.role
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.password is not None:
        user.hashed_password = hash_password(body.password)

    await db.commit()
    await db.refresh(user, ["user_stations"])
    return _out(user)


@router.delete("/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    if str(current.user_id) == user_id:
        raise HTTPException(400, "Cannot delete yourself")
    result = await db.execute(select(User).where(User.id == uuid.UUID(user_id)))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")
    await db.delete(user)
    await db.commit()


@router.put("/{user_id}/stations", response_model=UserOut)
async def update_user_stations(
    user_id: str,
    body: UserStationUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    """Assign which stations an OPERATOR can access"""
    result = await db.execute(
        select(User).options(selectinload(User.user_stations))
        .where(User.id == uuid.UUID(user_id))
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(404, "User not found")

    # Replace all station assignments
    for us in list(user.user_stations):
        await db.delete(us)

    for sid in body.station_ids:
        # Verify station exists
        st = await db.get(Station, uuid.UUID(sid))
        if st:
            db.add(UserStation(user_id=user.id, station_id=uuid.UUID(sid)))

    await db.commit()
    await db.refresh(user, ["user_stations"])
    return _out(user)
