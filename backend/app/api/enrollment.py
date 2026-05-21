from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.db.postgres import get_db
from app.db.qdrant import get_qdrant
from app.models.orm import Employee, FaceTemplate
from app.models.schemas import EnrollmentStatus, FaceTemplateOut
from app.core.config import get_settings
from app.core.face_engine import face_engine, anti_spoof_engine
from app.core.security import require_hr, CurrentUser
from app.db.redis import get_min_face_quality, get_anti_spoof_enabled, get_anti_spoof_threshold
from qdrant_client.models import PointStruct, PointIdsList
import uuid
import shutil
from pathlib import Path

router = APIRouter()
settings = get_settings()


@router.get("/{employee_id}/enrollment", response_model=EnrollmentStatus)
async def get_enrollment_status(
    employee_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    result = await db.execute(
        select(Employee).options(selectinload(Employee.face_templates)).where(Employee.id == employee_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, "Employee not found")

    slot_map = {t.sample_index: t for t in emp.face_templates}
    slots = []
    for i in range(6):
        if i in slot_map:
            t = slot_map[i]
            slots.append(
                FaceTemplateOut(
                    sample_index=t.sample_index,
                    quality_score=t.quality_score,
                    created_at=t.created_at,
                    image_url=f"/api/v1/employees/{employee_id}/enroll/{i}/image",
                )
            )
        else:
            slots.append(None)
    return EnrollmentStatus(
        employee_id=employee_id,
        slots=slots,
        completed=len(emp.face_templates),
        is_ready=len(emp.face_templates) >= settings.min_templates_to_activate,
    )


@router.get("/{employee_id}/enroll/{sample_index}/image")
async def get_face_image(
    employee_id: uuid.UUID,
    sample_index: int,
    db: AsyncSession = Depends(get_db),
    _: CurrentUser = Depends(require_hr),
):
    """ดึงรูปใบหน้าที่ enroll ไว้ (auth required — รูปเป็น sensitive data)"""
    result = await db.execute(
        select(Employee).options(selectinload(Employee.face_templates)).where(Employee.id == employee_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, "Employee not found")

    template = next((t for t in emp.face_templates if t.sample_index == sample_index), None)
    if not template:
        raise HTTPException(404, "Face template not found")

    img_path = Path(template.image_path)
    if not img_path.exists():
        raise HTTPException(404, "Image file not found on disk")

    return FileResponse(img_path, media_type="image/jpeg")


@router.post("/{employee_id}/enroll", status_code=201)
async def upload_face_sample(
    employee_id: uuid.UUID,
    sample_index: int = Form(...),
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    qdrant=Depends(get_qdrant),
    _: CurrentUser = Depends(require_hr),
):
    if not 0 <= sample_index <= 5:
        raise HTTPException(400, "sample_index must be 0–5")

    result = await db.execute(
        select(Employee).options(selectinload(Employee.face_templates)).where(Employee.id == employee_id)
    )
    emp = result.scalar_one_or_none()
    if not emp:
        raise HTTPException(404, "Employee not found")

    # Save image to disk
    img_dir = Path(settings.storage_path) / "faces" / str(employee_id)
    img_dir.mkdir(parents=True, exist_ok=True)
    img_path = img_dir / f"sample_{sample_index}.jpg"
    with img_path.open("wb") as f:
        shutil.copyfileobj(file.file, f)

    # Extract embedding
    import cv2

    img = cv2.imread(str(img_path))
    embeddings = face_engine.get_embeddings(img)
    if not embeddings:
        img_path.unlink(missing_ok=True)
        raise HTTPException(422, "No face detected in image")
    embedding = embeddings[0]

    # Anti-spoofing check (if enabled and model available)
    if await get_anti_spoof_enabled() and anti_spoof_engine.available:
        faces = face_engine.app.get(img)
        if faces:
            bbox = [int(v) for v in faces[0].bbox]
            threshold = await get_anti_spoof_threshold()
            is_live, spoof_score = anti_spoof_engine.check_liveness(img, bbox, threshold)
            if not is_live:
                img_path.unlink(missing_ok=True)
                raise HTTPException(
                    422,
                    f"Anti-spoofing failed — liveness score {spoof_score:.2f} < {threshold:.2f}. "
                    "Use a live face in good lighting, not a photo or screen.",
                )

    quality = face_engine.get_quality_score(img)
    min_quality = await get_min_face_quality()
    if quality < min_quality:
        img_path.unlink(missing_ok=True)
        raise HTTPException(
            422,
            f"Face quality too low ({quality:.2f} < {min_quality:.2f}) — "
            "ensure good lighting and face the camera directly",
        )

    # Remove existing template for this slot if any
    existing = next((t for t in emp.face_templates if t.sample_index == sample_index), None)
    if existing:
        await qdrant.delete(
            collection_name=settings.qdrant_collection,
            points_selector=PointIdsList(points=[str(existing.qdrant_id)]),
        )
        await db.delete(existing)
        await db.flush()  # ensure DELETE executes before INSERT (avoid unique constraint violation)

    # Insert into Qdrant
    qdrant_id = uuid.uuid4()
    await qdrant.upsert(
        collection_name=settings.qdrant_collection,
        points=[
            PointStruct(
                id=str(qdrant_id),
                vector=embedding.tolist(),
                payload={"employee_id": str(employee_id), "dept_id": emp.dept_id},
            )
        ],
    )

    # Save template record
    template = FaceTemplate(
        employee_id=employee_id,
        qdrant_id=qdrant_id,
        sample_index=sample_index,
        image_path=str(img_path),
        quality_score=float(quality),
    )
    db.add(template)

    # Activate employee if all 6 slots filled after this
    await db.flush()
    await db.refresh(emp, ["face_templates"])
    if len(emp.face_templates) >= settings.min_templates_to_activate:
        emp.is_active = True

    await db.commit()
    return {"sample_index": sample_index, "quality_score": float(quality)}


@router.delete("/{employee_id}/enroll/{sample_index}", status_code=204)
async def delete_face_sample(
    employee_id: uuid.UUID,
    sample_index: int,
    db: AsyncSession = Depends(get_db),
    qdrant=Depends(get_qdrant),
    _: CurrentUser = Depends(require_hr),
):
    result = await db.execute(
        select(FaceTemplate).where(
            FaceTemplate.employee_id == employee_id,
            FaceTemplate.sample_index == sample_index,
        )
    )
    template = result.scalar_one_or_none()
    if not template:
        raise HTTPException(404, "Template not found")

    await qdrant.delete(
        collection_name=settings.qdrant_collection,
        points_selector=PointIdsList(points=[str(template.qdrant_id)]),
    )
    Path(template.image_path).unlink(missing_ok=True)
    await db.delete(template)
    await db.commit()
