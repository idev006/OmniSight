"""
Auth API — DB-backed login with bcrypt + JWT (role + station_ids in token)
"""
import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.security import verify_password, create_access_token
from app.db.postgres import get_db
from app.models.orm import User, UserStation
from app.models.schemas import LoginRequest, TokenOut

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

    token = create_access_token(
        sub=user.username,
        role=user.role,
        user_id=str(user.id),
        station_ids=station_ids,
    )

    logger.info(f"Login: user={user.username} role={user.role}")
    return TokenOut(access_token=token)
