"""
Auth API — DB-backed login with bcrypt + JWT (role + station_ids in token)
"""

import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import (
    verify_password,
    create_access_token,
    get_current_user,
    CurrentUser,
)
from app.core.config import get_settings
from app.db.postgres import get_db
from app.models.orm import User, SystemSetting
from app.models.schemas import LoginRequest, TokenOut

_config = get_settings()

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/login", response_model=TokenOut)
async def login(body: LoginRequest, db: AsyncSession = Depends(get_db)):
    # Load user + stations in one query
    result = await db.execute(
        select(User)
        .options(selectinload(User.user_stations))
        .where(User.username == body.username, User.is_active == True)
    )
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    station_ids = [str(us.station_id) for us in user.user_stations]

    # Read token expiry from live DB setting (fallback to config)
    expire_hours = _config.access_token_expire_hours
    setting = await db.get(SystemSetting, "access_token_expire_hours")
    if setting:
        try:
            expire_hours = int(setting.value)
        except ValueError:
            pass

    token = create_access_token(
        sub=user.username,
        role=user.role,
        user_id=str(user.id),
        station_ids=station_ids,
        expire_hours=expire_hours,
    )

    logger.info(f"Login: user={user.username} role={user.role}")
    return TokenOut(access_token=token)


@router.get("/me")
async def get_me(
    current: CurrentUser = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Verify session and return live user info from DB.
    Called on app load to ensure user still exists and is active.
    Returns 401 if user has been deactivated since token was issued.
    """
    result = await db.execute(select(User).options(selectinload(User.user_stations)).where(User.id == current.user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")
    if not user.is_active:
        raise HTTPException(status_code=401, detail="Account has been deactivated")

    return {
        "user_id": str(user.id),
        "username": user.username,
        "full_name": user.full_name or "",
        "role": user.role,
        "is_active": user.is_active,
        "station_ids": [str(us.station_id) for us in user.user_stations],
    }
