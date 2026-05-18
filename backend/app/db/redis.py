import redis.asyncio as aioredis
from app.core.config import get_settings
import json
import logging

logger = logging.getLogger(__name__)
settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=True)

# ─── Station Filter ────────────────────────────────────────────────────────────

async def get_station_filter(station_id: str) -> list[int]:
    """ดึง dept_ids ของ station จาก Redis fallback ส่ง list ว่าง"""
    try:
        key = f"station:{station_id}:filter"
        data = await redis.get(key)
        return json.loads(data) if data else []
    except Exception:
        logger.warning(f"Redis unavailable — no dept filter for station {station_id}")
        return []


async def set_station_filter(station_id: str, dept_ids: list[int]):
    key = f"station:{station_id}:filter"
    await redis.set(key, json.dumps(dept_ids))


async def delete_station_filter(station_id: str):
    key = f"station:{station_id}:filter"
    await redis.delete(key)


# ─── Attendance Cooldown ───────────────────────────────────────────────────────

_COOLDOWN_DEFAULT = 300  # fallback ถ้า Redis/DB ไม่มีค่า


async def _get_cooldown_seconds() -> int:
    """อ่าน cooldown_seconds จาก Redis (write-through จาก Settings UI) — มีผลทันที"""
    try:
        val = await redis.get("setting:cooldown_seconds")
        if val:
            return max(10, int(val))   # minimum 10s ป้องกันค่าผิดพลาด
    except Exception:
        pass
    return _COOLDOWN_DEFAULT


async def check_attendance_cooldown(employee_id: str, station_id: str) -> bool:
    """
    ตรวจสอบว่าพนักงานเพิ่ง log ที่ station นี้ภายใน cooldown หรือยัง
    Returns True  = ยังอยู่ใน cooldown (ห้าม log ซ้ำ)
    Returns False = หมด cooldown แล้ว (log ได้)
    """
    try:
        key = f"cooldown:{employee_id}:{station_id}"
        return await redis.exists(key) == 1
    except Exception:
        logger.warning(f"Redis unavailable — skipping cooldown check for {employee_id}")
        return False  # ถ้า Redis ล่ม ยอมให้ log ได้ดีกว่า miss


async def get_min_face_quality() -> float:
    try:
        val = await redis.get("setting:min_face_quality")
        if val:
            return max(0.0, min(1.0, float(val)))
    except Exception:
        pass
    return 0.6


async def increment_unknown_count(station_id: str) -> int:
    """นับ unknown face ต่อ station ในช่วง 5 นาที — คืนค่า count ปัจจุบัน"""
    try:
        key = f"unknown_count:{station_id}"
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, 300)  # reset counter ทุก 5 นาที
        return count
    except Exception:
        return 0


async def get_unknown_alert_threshold() -> int:
    try:
        val = await redis.get("setting:unknown_face_alert")
        if val:
            return max(1, int(val))
    except Exception:
        pass
    return 5


async def set_attendance_cooldown(employee_id: str, station_id: str):
    """ตั้ง cooldown key โดย TTL อ่านจาก Settings UI แบบ real-time"""
    try:
        key = f"cooldown:{employee_id}:{station_id}"
        ttl = await _get_cooldown_seconds()
        await redis.setex(key, ttl, "1")
    except Exception:
        logger.warning(f"Redis unavailable — cooldown not set for {employee_id}")
