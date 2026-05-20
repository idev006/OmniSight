import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from prometheus_client import generate_latest, CONTENT_TYPE_LATEST

from app.core.config import get_settings
from app.db.postgres import async_session_factory
from app.db.qdrant import init_collection
from app.services.camera_manager import camera_manager

settings = get_settings()
from app.core.logging_config import setup_logging
setup_logging(settings.log_dir)
logger = logging.getLogger(__name__)


async def _seed_admin():
    """สร้าง admin user เริ่มต้น ถ้ายังไม่มีใน DB"""
    from sqlalchemy import select
    from app.models.orm import User, SystemSetting
    from app.core.security import hash_password

    DEFAULT_SETTINGS = [
        # Security
        ("access_token_expire_hours", "8",    "int",   "JWT access token lifetime (hours). Takes effect on next login."),
        # Face Recognition
        ("match_threshold",    "0.72",  "float",  "Minimum cosine similarity score for a face match (0.0–1.0)"),
        ("min_face_quality",   "0.6",   "float",  "Minimum quality score required during enrollment (0.0–1.0)"),
        # Attendance
        ("cooldown_seconds",      "300",  "int",  "Minimum seconds between two attendance records for the same person"),
        ("unknown_face_alert",    "5",    "int",  "Trigger alert after N unknown faces detected within 5 minutes"),
        ("late_threshold_minutes","15",   "int",  "Minutes after shift start_time before marking employee as LATE"),
        # Performance
        ("max_fps_per_camera", "2",     "int",    "Max frames per second the backend processes per camera"),
        ("inference_workers",  "2",     "int",    "Number of parallel ONNX inference workers (restart required)"),
        ("face_detect_size",   "320",   "int",    "Input resolution for face detector: 320 (fast, recommended) or 640 (accurate)"),
        # Anti-spoofing
        ("anti_spoof_enabled",   "0",   "int",    "Enable MiniFASNet anti-spoofing (1=on, 0=off). Requires model download."),
        ("anti_spoof_threshold", "0.6", "float",  "Minimum liveness score to accept as real face (0.0–1.0)"),
        # Notifications
        ("discord_webhook_url",  "",    "str",    "Discord Incoming Webhook URL for real-time alerts"),
        ("telegram_bot_token",   "",    "str",    "Telegram Bot Token (from @BotFather)"),
        ("telegram_chat_id",     "",    "str",    "Telegram Chat ID or Group ID to send alerts to"),
        ("slack_webhook_url",    "",    "str",    "Slack Incoming Webhook URL for real-time alerts"),
        ("notify_on_checkin",    "1",   "int",    "Send notification when employee checks in (1=on, 0=off)"),
        ("notify_on_unknown",    "1",   "int",    "Send notification on unknown face alert (1=on, 0=off)"),
        ("notify_on_spoof",      "1",   "int",    "Send notification when spoofing attempt is detected (1=on, 0=off)"),
        ("notify_on_absent",     "1",   "int",    "Send notification when employee is absent (checked every 5 min, 1=on, 0=off)"),
        # Line Notify
        ("line_notify_token",    "",    "str",    "Line Notify Token (from https://notify-bot.line.me/my/)"),
        # Email (SMTP)
        ("email_smtp_server",    "",    "str",    "SMTP server hostname (e.g., smtp.gmail.com)"),
        ("email_smtp_port",      "587", "int",    "SMTP port (587=TLS/STARTTLS, 465=SSL)"),
        ("email_smtp_user",      "",    "str",    "SMTP username / sender email address"),
        ("email_smtp_password",  "",    "str",    "SMTP password or App Password"),
        ("email_to_address",     "",    "str",    "Recipient email address for notifications"),
    ]

    async with async_session_factory() as db:
        # Seed admin user
        result = await db.execute(select(User).where(User.username == "admin"))
        if not result.scalar_one_or_none():
            admin = User(
                username="admin",
                hashed_password=hash_password("admin"),
                full_name="System Administrator",
                role="ADMIN",
            )
            db.add(admin)
            logger.info("Seeded default admin user (admin/admin)")

        # Seed system_settings
        for key, value, vtype, desc in DEFAULT_SETTINGS:
            existing = await db.get(SystemSetting, key)
            if not existing:
                db.add(SystemSetting(
                    key=key, value=value, value_type=vtype, description=desc
                ))

        await db.commit()

        # Sync all settings to Redis on startup so live-reload keys are always warm
        from app.db.redis import redis as _redis
        all_settings = await db.execute(select(SystemSetting))
        for s in all_settings.scalars().all():
            await _redis.set(f"setting:{s.key}", s.value)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_collection()
    await _seed_admin()

    # Init anti-spoof engine (lazy — won't load model until first use)
    from app.core.face_engine import anti_spoof_engine, face_engine
    from app.api.websocket import _executor
    anti_spoof_engine.init(settings.anti_spoof_model_dir)
    if anti_spoof_engine.available:
        logger.info("AntiSpoofEngine: MiniFASNet model found — anti-spoofing ready")
    else:
        logger.warning(
            "AntiSpoofEngine: model not found — anti-spoofing disabled. "
            "Run: python backend/scripts/download_anti_spoof_model.py"
        )

    # Warm up FaceEngine — load buffalo_l + JIT-compile ONNX kernels now,
    # so the first camera connection is not stalled by 5-10 s model init.
    logger.info("Warming up FaceEngine (buffalo_l)…")
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(_executor, face_engine.warmup)
    logger.info("FaceEngine warm-up done")

    # Start heartbeat monitor (background task)
    heartbeat_task = asyncio.create_task(camera_manager.heartbeat_monitor())

    # Start notification service (subscribes to omnisight:events Pub/Sub)
    from app.services.notification_service import notification_loop
    from app.services.absent_alert_service import absent_alert_loop
    from app.db.redis import redis as _redis
    notification_task  = asyncio.create_task(notification_loop(_redis))
    absent_alert_task  = asyncio.create_task(absent_alert_loop(_redis))

    from app.core.face_engine import get_best_provider
    active_provider = get_best_provider(settings.onnxruntime_provider)[0]
    logger.info(f"OmniSight started — ONNX Provider: {active_provider}")
    yield

    # Shutdown
    heartbeat_task.cancel()
    notification_task.cancel()
    absent_alert_task.cancel()
    try:
        await asyncio.gather(heartbeat_task, notification_task, absent_alert_task,
                             return_exceptions=True)
    except asyncio.CancelledError:
        pass


app = FastAPI(
    title="OmniSight API",
    version="0.2.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:5173",
        "http://192.168.1.170:5173",   # PC IP — มือถือใน network เดียวกัน
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/metrics", include_in_schema=False)
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)


@app.get("/health")
async def health():
    from app.core.face_engine import get_best_provider
    active = camera_manager.list_active()
    return {
        "status": "ok",
        "version": "0.2.0",
        "cameras_active": len(active),
        "onnx_provider": get_best_provider(settings.onnxruntime_provider)[0],
    }


# ── Routers ─────────────────────────────────────────────────────────────────
from app.api import (
    auth, departments, shifts, employees,
    stations, enrollment, attendance,
    websocket, console_ws, users, cameras, settings as settings_api,
    system,
)

app.include_router(auth.router,         prefix="/api/v1/auth",        tags=["auth"])
app.include_router(users.router,        prefix="/api/v1/users",       tags=["users"])
app.include_router(departments.router,  prefix="/api/v1/departments", tags=["departments"])
app.include_router(shifts.router,       prefix="/api/v1/shifts",      tags=["shifts"])
app.include_router(employees.router,    prefix="/api/v1/employees",   tags=["employees"])
app.include_router(stations.router,     prefix="/api/v1/stations",    tags=["stations"])
app.include_router(cameras.router,      prefix="/api/v1/cameras",     tags=["cameras"])
app.include_router(settings_api.router, prefix="/api/v1/settings",    tags=["settings"])
app.include_router(enrollment.router,   prefix="/api/v1/employees",   tags=["enrollment"])
app.include_router(attendance.router,   prefix="/api/v1/attendance",  tags=["attendance"])
app.include_router(system.router,       prefix="/api/v1/system",      tags=["system"])
app.include_router(websocket.router,    prefix="/api/v1/ws",          tags=["websocket"])
app.include_router(console_ws.router,   prefix="/api/v1/ws",          tags=["console"])
