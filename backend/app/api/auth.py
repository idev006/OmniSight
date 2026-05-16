from fastapi import APIRouter, HTTPException
from app.models.schemas import LoginRequest, TokenOut
from app.core.config import get_settings
from jose import jwt
from datetime import datetime, timedelta, timezone

router = APIRouter()
settings = get_settings()

# Single admin account — replace with DB users in production
_ADMIN_USER = "admin"
_ADMIN_PASS = "admin"


def _create_token(sub: str) -> str:
    exp = datetime.now(timezone.utc) + timedelta(hours=settings.access_token_expire_hours)
    return jwt.encode({"sub": sub, "exp": exp}, settings.secret_key, algorithm=settings.algorithm)


@router.post("/login", response_model=TokenOut)
async def login(body: LoginRequest):
    if body.username != _ADMIN_USER or body.password != _ADMIN_PASS:
        raise HTTPException(401, "Invalid credentials")
    return TokenOut(access_token=_create_token(body.username))
