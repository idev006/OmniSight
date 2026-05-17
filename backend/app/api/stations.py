from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from sqlalchemy.orm import selectinload
from app.db.postgres import get_db
from app.models.orm import Station, StationDepartment
from app.models.schemas import StationCreate, StationOut, StationDeptUpdate
from app.db.redis import set_station_filter, delete_station_filter
from app.core.security import get_current_user, require_admin, CurrentUser
import uuid

router = APIRouter()


@router.get("", response_model=list[StationOut])
async def list_stations(
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),   # all authenticated users (OPERATOR needs for scan)
):
    result = await db.execute(
        select(Station)
        .options(selectinload(Station.station_departments))
        .order_by(Station.name)
    )
    return [_enrich(s) for s in result.scalars().all()]


@router.post("", response_model=StationOut, status_code=201)
async def create_station(
    body: StationCreate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    station = Station(**body.model_dump())
    db.add(station)
    await db.commit()
    await db.refresh(station, ["station_departments"])
    return _enrich(station)


@router.get("/{station_id}", response_model=StationOut)
async def get_station(
    station_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(get_current_user),
):
    result = await db.execute(
        select(Station)
        .options(selectinload(Station.station_departments))
        .where(Station.id == station_id)
    )
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(404, "Station not found")
    return _enrich(station)


@router.put("/{station_id}/departments", response_model=StationOut)
async def update_station_departments(
    station_id: uuid.UUID,
    body: StationDeptUpdate,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_admin),
):
    result = await db.execute(
        select(Station)
        .options(selectinload(Station.station_departments))
        .where(Station.id == station_id)
    )
    station = result.scalar_one_or_none()
    if not station:
        raise HTTPException(404, "Station not found")

    await db.execute(
        delete(StationDepartment).where(StationDepartment.station_id == station_id)
    )
    for dept_id in body.dept_ids:
        db.add(StationDepartment(station_id=station_id, dept_id=dept_id))

    await db.commit()

    # Sync Redis filter
    if body.dept_ids:
        await set_station_filter(str(station_id), body.dept_ids)
    else:
        await delete_station_filter(str(station_id))

    await db.refresh(station, ["station_departments"])
    return _enrich(station)


def _enrich(station: Station) -> StationOut:
    return StationOut(
        id=station.id,
        name=station.name,
        location=station.location,
        is_active=station.is_active,
        dept_ids=[sd.dept_id for sd in station.station_departments],
    )
