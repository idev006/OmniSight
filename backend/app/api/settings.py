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

# ── Value validators ────────────────────────────────────────────────────────
# (type, min, max)  or  (type, [allowed_values])
# String settings (webhook URLs, tokens, etc.) ไม่ต้อง validate ค่า
_VALIDATORS: dict[str, tuple] = {
    "access_token_expire_hours": ("int",   1,    720),
    "match_threshold":           ("float", 0.1,  1.0),
    "min_face_quality":          ("float", 0.1,  1.0),
    "cooldown_seconds":          ("int",   10,   86400),
    "unknown_face_alert":        ("int",   1,    1000),
    "late_threshold_minutes":    ("int",   0,    480),
    "max_fps_per_camera":        ("int",   1,    30),
    "inference_workers":         ("int",   1,    32),
    "face_detect_size":          ("int",   [320, 640]),   # only valid ONNX sizes
    "anti_spoof_enabled":        ("int",   [0,   1]),
    "anti_spoof_threshold":      ("float", 0.1,  1.0),
    "notify_on_checkin":         ("int",   [0,   1]),
    "notify_on_unknown":         ("int",   [0,   1]),
    "notify_on_spoof":           ("int",   [0,   1]),
    "notify_on_absent":          ("int",   [0,   1]),
    "email_smtp_port":           ("int",   1,    65535),
}


def _validate_value(key: str, raw: str) -> str:
    """
    ตรวจสอบค่า setting ก่อน save
    - คืน string ที่ clean แล้ว (cast แล้ว str() กลับ เพื่อ normalize)
    - raise HTTPException 422 ถ้าค่าผิด
    - ถ้า key ไม่มีใน _VALIDATORS (string settings) คืน raw ตรงๆ
    """
    spec = _VALIDATORS.get(key)
    if not spec:
        return raw   # URL / token / email — ไม่ validate ค่า

    vtype, *rest = spec
    try:
        v: float | int = int(raw) if vtype == "int" else float(raw)
    except (ValueError, TypeError):
        raise HTTPException(422, detail=f"'{key}' ต้องเป็นตัวเลขประเภท {vtype}")

    if len(rest) == 1 and isinstance(rest[0], list):
        allowed = rest[0]
        if v not in allowed:
            raise HTTPException(422, detail=f"'{key}' ต้องเป็นหนึ่งใน {allowed}")
    elif len(rest) == 2:
        lo, hi = rest
        if not (lo <= v <= hi):
            raise HTTPException(422, detail=f"'{key}' ต้องอยู่ระหว่าง {lo}–{hi} (ได้รับ {v})")

    return str(v)  # normalize (เช่น "1.0" → "1.0", "01" → "1")


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

    # Validate before save — prevents crash-inducing values
    clean_value = _validate_value(key, str(body.value))
    s.value = clean_value
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
