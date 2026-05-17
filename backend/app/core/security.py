"""
Security utilities: password hashing, JWT creation/verification, FastAPI dependencies
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.config import get_settings
from app.db.postgres import get_db

settings = get_settings()

# ─── Password ─────────────────────────────────────────────────────────────────

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

def hash_password(plain: str) -> str:
    return pwd_context.hash(plain)

def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


# ─── JWT ──────────────────────────────────────────────────────────────────────

def create_access_token(sub: str, role: str, user_id: str,
                        station_ids: list[str] | None = None) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.access_token_expire_hours)
    payload = {
        "sub": sub,
        "role": role,
        "user_id": user_id,
        "station_ids": station_ids or [],
        "exp": exp,
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.algorithm)


def decode_token(token: str) -> dict:
    try:
        return jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid or expired token")


# ─── FastAPI Dependencies ──────────────────────────────────────────────────────

bearer_scheme = HTTPBearer(auto_error=False)


class CurrentUser:
    def __init__(self, user_id: str, username: str, role: str,
                 station_ids: list[str]):
        self.user_id = user_id
        self.username = username
        self.role = role
        self.station_ids = station_ids

    @property
    def is_admin(self) -> bool:
        return self.role == "ADMIN"

    @property
    def is_hr(self) -> bool:
        return self.role in ("ADMIN", "HR")

    def can_access_station(self, station_id: str) -> bool:
        if self.role in ("ADMIN", "HR"):
            return True
        return station_id in self.station_ids


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> CurrentUser:
    if not credentials:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(credentials.credentials)
    return CurrentUser(
        user_id=payload.get("user_id", ""),
        username=payload.get("sub", ""),
        role=payload.get("role", "OPERATOR"),
        station_ids=payload.get("station_ids", []),
    )


async def require_admin(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Admin role required")
    return user


async def require_hr(user: CurrentUser = Depends(get_current_user)) -> CurrentUser:
    if not user.is_hr:
        raise HTTPException(status_code=403, detail="HR or Admin role required")
    return user


def get_current_user_ws(token: str) -> CurrentUser:
    """WebSocket version — token from query param (not header)"""
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")
    payload = decode_token(token)
    return CurrentUser(
        user_id=payload.get("user_id", ""),
        username=payload.get("sub", ""),
        role=payload.get("role", "OPERATOR"),
        station_ids=payload.get("station_ids", []),
    )
