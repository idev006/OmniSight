"""
System Settings API — Live Config (ADMIN only)
เปลี่ยน setting มีผลทันที ไม่ต้อง restart
"""
import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.security import require_admin, CurrentUser
from app.db.postgres import get_db
from app.db.redis import redis
from app.models.orm import SystemSetting
from app.models.schemas import SystemSettingOut, SystemSettingUpdate

logger = logging.getLogger(__name__)
router = APIRouter()

# Settings ที่มีผลทันที vs ต้องการ graceful restart
LIVENESS = {
    # Security
    "access_token_expire_hours": "graceful",   # new tokens only
    # Face Recognition
    "match_threshold":    "live",
    "min_face_quality":   "live",
    # Attendance
    "cooldown_seconds":   "live",
    "unknown_face_alert": "live",
    # Performance
    "max_fps_per_camera": "live",
    "inference_workers":  "restart",
    "face_detect_size":   "restart",
}


@router.get("", response_model=list[SystemSettingOut])
async def list_settings(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    result = await db.execute(select(SystemSetting).order_by(SystemSetting.key))
    settings = result.scalars().all()
    out = []
    for s in settings:
        so = SystemSettingOut.model_validate(s)
        so.liveness = LIVENESS.get(s.key, "live")
        out.append(so)
    return out


@router.get("/{key}", response_model=SystemSettingOut)
async def get_setting(
    key: str,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    s = await db.get(SystemSetting, key)
    if not s:
        raise HTTPException(404, f"Setting '{key}' not found")
    out = SystemSettingOut.model_validate(s)
    out.liveness = LIVENESS.get(key, "live")
    return out


@router.put("/{key}", response_model=SystemSettingOut)
async def update_setting(
    key: str,
    body: SystemSettingUpdate,
    db: AsyncSession = Depends(get_db),
    current: CurrentUser = Depends(require_admin),
):
    s = await db.get(SystemSetting, key)
    if not s:
        raise HTTPException(404, f"Setting '{key}' not found")

    s.value = str(body.value)
    s.updated_by = current.user_id
    s.updated_at = datetime.now(timezone.utc)
    await db.commit()
    await db.refresh(s)

    # Write-through to Redis cache
    try:
        await redis.set(f"setting:{key}", str(body.value))
        # Publish config_changed event → all backend instances + Pilot Console
        await redis.publish("omnisight:events", json.dumps({
            "event": "config_changed",
            "key": key,
            "value": str(body.value),
            "updated_by": current.username,
        }))
    except Exception as e:
        logger.warning(f"Redis publish failed for setting {key}: {e}")

    logger.info(f"Setting updated: {key}={body.value} by {current.username}")
    out = SystemSettingOut.model_validate(s)
    out.liveness = LIVENESS.get(key, "live")
    return out
