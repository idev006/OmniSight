import redis.asyncio as aioredis
from app.core.config import get_settings
import json

settings = get_settings()
redis = aioredis.from_url(settings.redis_url, decode_responses=True)


async def get_station_filter(station_id: str) -> list[int]:
    key = f"station:{station_id}:filter"
    data = await redis.get(key)
    return json.loads(data) if data else []


async def set_station_filter(station_id: str, dept_ids: list[int]):
    key = f"station:{station_id}:filter"
    await redis.set(key, json.dumps(dept_ids))


async def delete_station_filter(station_id: str):
    key = f"station:{station_id}:filter"
    await redis.delete(key)
