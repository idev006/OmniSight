"""
Real-time notification service — Discord, Telegram, Slack.

Subscribes to Redis Pub/Sub channel `omnisight:events` and forwards
events to configured channels based on admin settings.

Events handled:
  attendance_match    → notify if notify_on_checkin = 1
  unknown_face_alert  → notify if notify_on_unknown = 1
  spoof_detected      → notify if notify_on_spoof = 1

Settings (stored in system_settings / Redis):
  discord_webhook_url
  telegram_bot_token
  telegram_chat_id
  slack_webhook_url
  notify_on_checkin     1/0
  notify_on_unknown     1/0
  notify_on_spoof       1/0
"""

from __future__ import annotations

import asyncio
import json
import logging

import httpx

logger = logging.getLogger(__name__)

# ── helpers ───────────────────────────────────────────────────────────────────

async def _get_setting(redis, key: str) -> str:
    try:
        val = await redis.get(f"setting:{key}")
        return val or ""
    except Exception:
        return ""


async def _send_discord(webhook_url: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(webhook_url, json={"content": text})


async def _send_telegram(token: str, chat_id: str, text: str) -> None:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(url, json={"chat_id": chat_id, "text": text})


async def _send_slack(webhook_url: str, text: str) -> None:
    async with httpx.AsyncClient(timeout=5) as client:
        await client.post(webhook_url, json={"text": text})


async def _dispatch(redis, text: str) -> None:
    """Send text to every configured channel. Errors are logged, not raised."""
    tasks = []

    discord_url = await _get_setting(redis, "discord_webhook_url")
    if discord_url:
        tasks.append(_send_discord(discord_url, text))

    tg_token   = await _get_setting(redis, "telegram_bot_token")
    tg_chat_id = await _get_setting(redis, "telegram_chat_id")
    if tg_token and tg_chat_id:
        tasks.append(_send_telegram(tg_token, tg_chat_id, text))

    slack_url = await _get_setting(redis, "slack_webhook_url")
    if slack_url:
        tasks.append(_send_slack(slack_url, text))

    if not tasks:
        return

    results = await asyncio.gather(*tasks, return_exceptions=True)
    for r in results:
        if isinstance(r, Exception):
            logger.warning(f"Notification dispatch error: {r}")


# ── event formatters ──────────────────────────────────────────────────────────

def _fmt_checkin(data: dict) -> str:
    name     = data.get("full_name", "Unknown")
    dept     = data.get("dept_name") or ""
    station  = data.get("station_id", "")
    ts       = data.get("timestamp", "")[:19].replace("T", " ")
    dept_str = f" — {dept}" if dept else ""
    return f"✅ Check-in: {name}{dept_str}\n🚪 {station}  🕐 {ts}"


def _fmt_unknown(data: dict) -> str:
    station = data.get("station_id", "")
    camera  = data.get("camera_id", "")
    count   = data.get("count", "?")
    ts      = data.get("timestamp", "")[:19].replace("T", " ")
    return f"🚨 Unknown face alert\n📷 {camera} @ {station}  count={count}  🕐 {ts}"


def _fmt_spoof(data: dict) -> str:
    station = data.get("station_id", "")
    camera  = data.get("camera_id", "")
    ts      = data.get("timestamp", "")[:19].replace("T", " ")
    return f"🚫 Spoofing attempt detected\n📷 {camera} @ {station}  🕐 {ts}"


# ── main loop ─────────────────────────────────────────────────────────────────

async def notification_loop(redis) -> None:
    """
    Background task — call from main.py lifespan.
    Subscribes to omnisight:events and forwards to configured channels.
    """
    pubsub = redis.pubsub()
    await pubsub.subscribe("omnisight:events")
    logger.info("NotificationService: subscribed to omnisight:events")

    try:
        async for message in pubsub.listen():
            if message["type"] != "message":
                continue
            try:
                data = json.loads(message["data"])
            except Exception:
                continue

            event = data.get("event", "")

            try:
                if event == "attendance_match":
                    if await _get_setting(redis, "notify_on_checkin") == "1":
                        await _dispatch(redis, _fmt_checkin(data))

                elif event == "unknown_face_alert":
                    if await _get_setting(redis, "notify_on_unknown") == "1":
                        await _dispatch(redis, _fmt_unknown(data))

                elif event == "spoof_detected":
                    if await _get_setting(redis, "notify_on_spoof") == "1":
                        await _dispatch(redis, _fmt_spoof(data))

            except Exception as e:
                logger.warning(f"NotificationService event error ({event}): {e}")

    except asyncio.CancelledError:
        pass
    finally:
        await pubsub.unsubscribe("omnisight:events")
        logger.info("NotificationService: stopped")
