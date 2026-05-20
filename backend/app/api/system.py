"""
System Info API — admin-only endpoint
GET /api/v1/system/info

Returns live status of all services:
  - App version + uptime + ONNX provider
  - Face engine + anti-spoof
  - PostgreSQL (version, db size, row counts)
  - Qdrant (vector count, collection info)
  - Redis (memory, clients, uptime)
  - Storage (snapshot count + size)
"""
import os
import time
import logging
from pathlib import Path

from fastapi import APIRouter, Depends
from sqlalchemy import text

from app.core.config import get_settings
from app.core.security import require_admin
from app.core.face_engine import face_engine, anti_spoof_engine, get_best_provider
from app.db.postgres import async_session_factory
from app.db.qdrant import qdrant as _qdrant, get_qdrant_sync
from app.db.redis import redis as _redis

logger   = logging.getLogger(__name__)
router   = APIRouter()
settings = get_settings()

_START_TIME = time.time()   # module loaded at startup


@router.get("/info", dependencies=[Depends(require_admin)])
async def system_info():
    result = {
        "app":        _app_info(),
        "face_engine": _face_engine_info(),
        "anti_spoof": _anti_spoof_info(),
        "postgres":   await _postgres_info(),
        "qdrant":     await _qdrant_info(),
        "redis":      await _redis_info(),
        "storage":    _storage_info(),
    }
    return result


# ── App ───────────────────────────────────────────────────────────────────────

def _app_info() -> dict:
    uptime = int(time.time() - _START_TIME)
    provider = get_best_provider(settings.onnxruntime_provider)[0]
    return {
        "version":          "0.2.0",
        "uptime_seconds":   uptime,
        "onnx_provider":    provider,
        "face_detect_size": settings.face_detect_size,
        "inference_workers": settings.inference_workers,
        "storage_path":     settings.storage_path,
    }


# ── Face Engine ───────────────────────────────────────────────────────────────

def _face_engine_info() -> dict:
    loaded = face_engine._app is not None
    return {
        "status":  "ok" if loaded else "not_loaded",
        "model":   "buffalo_l",
        "det_size": settings.face_detect_size,
        "loaded":  loaded,
    }


# ── Anti-Spoof ────────────────────────────────────────────────────────────────

def _anti_spoof_info() -> dict:
    return {
        "available": anti_spoof_engine.available,
        "model":     "MiniFASNetV2 (2.7_80x80)",
        "model_path": str(Path(settings.anti_spoof_model_dir) / "2.7_80x80_MiniFASNetV2.onnx"),
        "note": "Suitable for webcam enrollment only — not for mobile scan (JPEG compression degrades texture)",
    }


# ── PostgreSQL ────────────────────────────────────────────────────────────────

async def _postgres_info() -> dict:
    try:
        async with async_session_factory() as db:
            # Version
            ver = (await db.execute(text("SELECT version()"))).scalar()
            ver_short = ver.split(",")[0] if ver else "unknown"

            # DB size
            size_bytes = (await db.execute(
                text("SELECT pg_database_size(current_database())")
            )).scalar() or 0

            # Row counts
            employees   = (await db.execute(text("SELECT COUNT(*) FROM employees"))).scalar()
            active_emp  = (await db.execute(text("SELECT COUNT(*) FROM employees WHERE is_active = true"))).scalar()
            enrolled    = (await db.execute(
                text("SELECT COUNT(DISTINCT employee_id) FROM face_templates")
            )).scalar()
            templates   = (await db.execute(text("SELECT COUNT(*) FROM face_templates"))).scalar()
            attendance  = (await db.execute(text("SELECT COUNT(*) FROM attendance_logs"))).scalar()
            departments = (await db.execute(text("SELECT COUNT(*) FROM departments"))).scalar()
            stations    = (await db.execute(text("SELECT COUNT(*) FROM stations"))).scalar()
            users       = (await db.execute(text("SELECT COUNT(*) FROM users"))).scalar()

        return {
            "status":       "ok",
            "version":      ver_short,
            "size_mb":      round(size_bytes / 1024 / 1024, 2),
            "url":          settings.database_url.split("@")[-1],   # hide credentials
            "rows": {
                "employees":        employees,
                "employees_active": active_emp,
                "employees_enrolled": enrolled,
                "face_templates":   templates,
                "attendance_logs":  attendance,
                "departments":      departments,
                "stations":         stations,
                "users":            users,
            },
        }
    except Exception as e:
        logger.warning("system_info postgres error: %s", e)
        return {"status": "error", "error": str(e)}


# ── Qdrant ────────────────────────────────────────────────────────────────────

async def _qdrant_info() -> dict:
    try:
        info = await _qdrant.get_collection(settings.qdrant_collection)
        return {
            "status":          "ok",
            "host":            f"{settings.qdrant_host}:{settings.qdrant_port}",
            "collection":      settings.qdrant_collection,
            "vectors_count":   info.vectors_count or 0,
            "points_count":    info.points_count  or 0,
            "vector_size":     512,
            "distance":        "Cosine",
            "quantization":    "SQ8",
        }
    except Exception as e:
        logger.warning("system_info qdrant error: %s", e)
        return {"status": "error", "error": str(e)}


# ── Redis ─────────────────────────────────────────────────────────────────────

async def _redis_info() -> dict:
    try:
        info = await _redis.info()
        return {
            "status":           "ok",
            "url":              settings.redis_url,
            "version":          info.get("redis_version", "unknown"),
            "used_memory_mb":   round(info.get("used_memory", 0) / 1024 / 1024, 2),
            "peak_memory_mb":   round(info.get("used_memory_peak", 0) / 1024 / 1024, 2),
            "connected_clients": info.get("connected_clients", 0),
            "uptime_seconds":   info.get("uptime_in_seconds", 0),
            "keyspace":         info.get("db0", "empty"),
        }
    except Exception as e:
        logger.warning("system_info redis error: %s", e)
        return {"status": "error", "error": str(e)}


# ── Storage ───────────────────────────────────────────────────────────────────

def _storage_info() -> dict:
    try:
        storage = Path(settings.storage_path)
        snapshot_dir = storage / "snapshots"

        # Count snapshots and total size
        count, total_bytes = 0, 0
        if snapshot_dir.exists():
            for root, _, files in os.walk(snapshot_dir):
                for f in files:
                    if f.endswith(".jpg"):
                        count += 1
                        total_bytes += os.path.getsize(os.path.join(root, f))

        # Disk usage of storage root
        import shutil
        disk = shutil.disk_usage(str(storage)) if storage.exists() else None

        return {
            "status":         "ok",
            "path":           str(storage),
            "snapshots_count": count,
            "snapshots_mb":   round(total_bytes / 1024 / 1024, 2),
            "disk_free_gb":   round(disk.free / 1024**3, 1) if disk else None,
            "disk_total_gb":  round(disk.total / 1024**3, 1) if disk else None,
        }
    except Exception as e:
        logger.warning("system_info storage error: %s", e)
        return {"status": "error", "error": str(e)}
