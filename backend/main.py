import asyncio
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.db.postgres import async_session_factory
from app.db.qdrant import init_collection
from app.services.camera_manager import camera_manager

settings = get_settings()
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
        ("cooldown_seconds",   "300",   "int",    "Minimum seconds between two attendance records for the same person"),
        ("unknown_face_alert", "5",     "int",    "Trigger alert after N unknown faces detected within 5 minutes"),
        # Performance
        ("max_fps_per_camera", "2",     "int",    "Max frames per second the backend processes per camera"),
        ("inference_workers",  "2",     "int",    "Number of parallel ONNX inference workers (restart required)"),
        ("face_detect_size",   "640",   "int",    "Input resolution for face detector: 320 (fast) or 640 (accurate)"),
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await init_collection()
    await _seed_admin()

    # Start heartbeat monitor (background task)
    heartbeat_task = asyncio.create_task(camera_manager.heartbeat_monitor())

    logger.info(f"OmniSight started — ONNX Provider: {settings.onnxruntime_provider}")
    yield

    # Shutdown
    heartbeat_task.cancel()
    try:
        await heartbeat_task
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


@app.get("/health")
async def health():
    active = camera_manager.list_active()
    return {
        "status": "ok",
        "version": "0.2.0",
        "cameras_active": len(active),
    }


# ── Routers ─────────────────────────────────────────────────────────────────
from app.api import (
    auth, departments, shifts, employees,
    stations, enrollment, attendance,
    websocket, console_ws, users, cameras, settings as settings_api,
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
app.include_router(websocket.router,    prefix="/api/v1/ws",          tags=["websocket"])
app.include_router(console_ws.router,   prefix="/api/v1/ws",          tags=["console"])
