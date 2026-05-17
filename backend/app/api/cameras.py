"""
Camera Management API
CRUD for cameras + live status from CameraManager
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import uuid

from app.core.security import require_admin, require_hr, CurrentUser
from app.db.postgres import get_db
from app.models.orm import Camera, Station
from app.models.schemas import CameraCreate, CameraOut, CameraUpdate
from app.services.camera_manager import camera_manager

router = APIRouter()


@router.get("", response_model=list[CameraOut])
async def list_cameras(
    station_id: str | None = None,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    q = select(Camera)
    if station_id:
        q = q.where(Camera.station_id == uuid.UUID(station_id))
    result = await db.execute(q.order_by(Camera.name))
    cameras = result.scalars().all()

    # Enrich with live status from CameraManager
    out = []
    for cam in cameras:
        cam_out = CameraOut.model_validate(cam)
        live = camera_manager.get_status(str(cam.id))
        cam_out.live_status = live.get("status", "offline")
        cam_out.live_fps = live.get("fps", 0.0)
        out.append(cam_out)
    return out


@router.post("", response_model=CameraOut, status_code=201)
async def create_camera(
    body: CameraCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    # Verify station exists
    station = await db.get(Station, uuid.UUID(str(body.station_id)))
    if not station:
        raise HTTPException(404, "Station not found")

    cam = Camera(**body.model_dump())
    db.add(cam)
    await db.commit()
    await db.refresh(cam)
    out = CameraOut.model_validate(cam)
    out.live_status = "offline"
    out.live_fps = 0.0
    return out


@router.get("/{camera_id}", response_model=CameraOut)
async def get_camera(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    cam = await db.get(Camera, uuid.UUID(camera_id))
    if not cam:
        raise HTTPException(404, "Camera not found")
    out = CameraOut.model_validate(cam)
    live = camera_manager.get_status(camera_id)
    out.live_status = live.get("status", "offline")
    out.live_fps = live.get("fps", 0.0)
    return out


@router.put("/{camera_id}", response_model=CameraOut)
async def update_camera(
    camera_id: str,
    body: CameraUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    cam = await db.get(Camera, uuid.UUID(camera_id))
    if not cam:
        raise HTTPException(404, "Camera not found")

    for field, val in body.model_dump(exclude_none=True).items():
        setattr(cam, field, val)

    await db.commit()
    await db.refresh(cam)
    out = CameraOut.model_validate(cam)
    live = camera_manager.get_status(camera_id)
    out.live_status = live.get("status", "offline")
    out.live_fps = live.get("fps", 0.0)
    return out


@router.delete("/{camera_id}", status_code=204)
async def delete_camera(
    camera_id: str,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    cam = await db.get(Camera, uuid.UUID(camera_id))
    if not cam:
        raise HTTPException(404, "Camera not found")

    # Gracefully disconnect if active
    await camera_manager.disconnect(camera_id, reason="Camera deleted")

    await db.delete(cam)
    await db.commit()


@router.post("/{camera_id}/pause", status_code=200)
async def pause_camera(
    camera_id: str,
    _: CurrentUser = Depends(require_admin),
):
    ok = await camera_manager.pause(camera_id)
    if not ok:
        raise HTTPException(404, "Camera not connected")
    return {"status": "paused", "camera_id": camera_id}


@router.post("/{camera_id}/resume", status_code=200)
async def resume_camera(
    camera_id: str,
    _: CurrentUser = Depends(require_admin),
):
    ok = await camera_manager.resume(camera_id)
    if not ok:
        raise HTTPException(404, "Camera not connected")
    return {"status": "active", "camera_id": camera_id}
