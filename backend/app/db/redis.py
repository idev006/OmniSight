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

COOLDOWN_SECONDS = 300  # 5 นาที


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


async def set_attendance_cooldown(employee_id: str, station_id: str):
    """ตั้ง cooldown key พร้อม TTL 5 นาที"""
    try:
        key = f"cooldown:{employee_id}:{station_id}"
        await redis.setex(key, COOLDOWN_SECONDS, "1")
    except Exception:
        logger.warning(f"Redis unavailable — cooldown not set for {employee_id}")
