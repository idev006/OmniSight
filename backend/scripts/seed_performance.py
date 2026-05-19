"""
seed_performance.py — สร้างพนักงาน 1,000 คน + face vectors จำลองใน Qdrant
ใช้สำหรับ performance/load test

Usage (from project root):
    my_env/Scripts/python.exe backend/scripts/seed_performance.py
    my_env/Scripts/python.exe backend/scripts/seed_performance.py --employees 500
    my_env/Scripts/python.exe backend/scripts/seed_performance.py --clear   # ลบ EMP* แล้ว seed ใหม่
"""
import asyncio
import sys
import uuid
import time
import argparse
from pathlib import Path
from datetime import time as dtime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
from sqlalchemy import select, text
from qdrant_client.models import PointStruct

from app.core.config import get_settings
from app.db.postgres import async_session_factory
from app.db.qdrant import qdrant, init_collection, COLLECTION, VECTOR_SIZE
from app.models.orm import Employee, Department, Shift, FaceTemplate

settings = get_settings()

# ── Constants ──────────────────────────────────────────────────────────────
DEPARTMENTS = [
    "Engineering", "Human Resources", "Finance", "Operations", "Sales",
    "Marketing", "IT Support", "Security", "Maintenance", "Management",
]
SHIFTS = [
    ("Morning",   dtime(8,  0), dtime(17, 0)),
    ("Afternoon", dtime(13, 0), dtime(22, 0)),
    ("Night",     dtime(22, 0), dtime(7,  0)),
]
TEMPLATES_PER_EMP = 6
EMP_BATCH         = 150   # rows per DB flush
QDRANT_BATCH      = 600   # points per Qdrant upsert


def _rand_unit_vector() -> list[float]:
    """Random normalized 512-dim vector — จำลอง InsightFace normed_embedding."""
    v = np.random.randn(VECTOR_SIZE).astype(np.float32)
    v /= np.linalg.norm(v)
    return v.tolist()


def _bar(done: int, total: int, width: int = 30) -> str:
    filled = int(width * done / total)
    return f"[{'#'*filled}{'.'*(width-filled)}] {done:>{len(str(total))}}/{total}"


# ── Seed helpers ───────────────────────────────────────────────────────────
async def _ensure_departments(db) -> dict[str, int]:
    result = await db.execute(select(Department))
    existing = {d.name: d.id for d in result.scalars().all()}
    for name in DEPARTMENTS:
        if name not in existing:
            db.add(Department(name=name))
    await db.flush()
    result = await db.execute(select(Department))
    return {d.name: d.id for d in result.scalars().all()}


async def _ensure_shifts(db) -> dict[str, int]:
    result = await db.execute(select(Shift))
    existing = {s.name: s.id for s in result.scalars().all()}
    for name, start, end in SHIFTS:
        if name not in existing:
            db.add(Shift(name=name, start_time=start, end_time=end))
    await db.flush()
    result = await db.execute(select(Shift))
    return {s.name: s.id for s in result.scalars().all()}


# ── Main seed ──────────────────────────────────────────────────────────────
async def seed(n_employees: int, clear: bool):
    total_vectors = n_employees * TEMPLATES_PER_EMP
    print(f"\n{'='*58}")
    print(f"  OmniSight Performance Seed")
    print(f"  Employees : {n_employees:,}  x  {TEMPLATES_PER_EMP} templates  =  {total_vectors:,} vectors")
    print(f"{'='*58}\n")

    t0 = time.perf_counter()

    # Qdrant collection (idempotent)
    await init_collection()

    async with async_session_factory() as db:
        async with db.begin():

            # ── Clear existing seed data ────────────────────────────────
            if clear:
                print("[!] --clear: removing existing EMP* employees ...")
                result = await db.execute(
                    text("SELECT COUNT(*) FROM employees WHERE emp_code LIKE 'EMP%'")
                )
                existing_count = result.scalar()
                await db.execute(
                    text("DELETE FROM employees WHERE emp_code LIKE 'EMP%'")
                )
                print(f"    Deleted {existing_count:,} employees (cascade -> face_templates)")
                print("    Note: run reconcile_qdrant.py to clean up orphaned Qdrant vectors\n")

            # ── Departments & Shifts ────────────────────────────────────
            print("-> Ensuring Departments & Shifts ...")
            dept_map  = await _ensure_departments(db)
            shift_map = await _ensure_shifts(db)
            dept_ids  = list(dept_map.values())
            shift_ids = list(shift_map.values())
            print(f"   Departments : {len(dept_map)}  |  Shifts : {len(shift_map)}\n")

            # ── Check existing employees ────────────────────────────────
            result = await db.execute(select(Employee.emp_code))
            existing_codes = {row[0] for row in result.all()}

            codes_to_create = [
                f"EMP{i:05d}" for i in range(1, n_employees + 1)
                if f"EMP{i:05d}" not in existing_codes
            ]
            skip_count = n_employees - len(codes_to_create)

            if not codes_to_create:
                print(f"[OK] All {n_employees:,} employees already exist. Nothing to do.")
                return
            if skip_count:
                print(f"   Skipping {skip_count:,} existing  |  Creating {len(codes_to_create):,} new\n")

            # ── Create Employees ────────────────────────────────────────
            print(f"[1/2] Creating {len(codes_to_create):,} employees ...")
            t1 = time.perf_counter()
            employees_created: list[Employee] = []

            for batch_start in range(0, len(codes_to_create), EMP_BATCH):
                batch_codes = codes_to_create[batch_start:batch_start + EMP_BATCH]
                batch: list[Employee] = []
                for i, code in enumerate(batch_codes):
                    idx = batch_start + i
                    emp = Employee(
                        id=uuid.uuid4(),
                        emp_code=code,
                        full_name=f"Test Employee {code}",
                        dept_id=dept_ids[idx % len(dept_ids)],
                        shift_id=shift_ids[idx % len(shift_ids)],
                        is_active=True,
                    )
                    batch.append(emp)
                db.add_all(batch)
                await db.flush()
                employees_created.extend(batch)
                print(f"\r  {_bar(len(employees_created), len(codes_to_create))}  "
                      f"{time.perf_counter()-t1:.1f}s", end="", flush=True)

            print(f"\r  {_bar(len(employees_created), len(codes_to_create))}  "
                  f"{time.perf_counter()-t1:.1f}s  done\n")

            # ── Create FaceTemplates + Qdrant vectors ───────────────────
            print(f"[2/2] Creating {total_vectors:,} face templates + Qdrant vectors ...")
            t2 = time.perf_counter()
            templates_done = 0
            qdrant_buf: list[PointStruct] = []

            for batch_start in range(0, len(employees_created), EMP_BATCH):
                emp_batch = employees_created[batch_start:batch_start + EMP_BATCH]
                tpl_batch: list[FaceTemplate] = []

                for emp in emp_batch:
                    for slot in range(TEMPLATES_PER_EMP):
                        qid = uuid.uuid4()
                        tpl_batch.append(FaceTemplate(
                            id=uuid.uuid4(),
                            employee_id=emp.id,
                            qdrant_id=qid,
                            sample_index=slot,
                            image_path=f"storage/faces/{emp.id}/sample_{slot}.jpg",
                            quality_score=round(0.75 + np.random.random() * 0.24, 4),
                        ))
                        qdrant_buf.append(PointStruct(
                            id=str(qid),
                            vector=_rand_unit_vector(),
                            payload={
                                "employee_id": str(emp.id),
                                "dept_id": emp.dept_id,
                            },
                        ))

                        if len(qdrant_buf) >= QDRANT_BATCH:
                            await qdrant.upsert(
                                collection_name=COLLECTION,
                                points=qdrant_buf,
                                wait=False,
                            )
                            qdrant_buf.clear()

                db.add_all(tpl_batch)
                await db.flush()
                templates_done += len(tpl_batch)
                print(f"\r  {_bar(templates_done, total_vectors)}  "
                      f"{time.perf_counter()-t2:.1f}s", end="", flush=True)

            # flush remaining Qdrant points (wait=True to confirm)
            if qdrant_buf:
                await qdrant.upsert(
                    collection_name=COLLECTION,
                    points=qdrant_buf,
                    wait=True,
                )

            print(f"\r  {_bar(templates_done, total_vectors)}  "
                  f"{time.perf_counter()-t2:.1f}s  done\n")

    # ── Summary ────────────────────────────────────────────────────────────
    elapsed = time.perf_counter() - t0
    info = await qdrant.get_collection(COLLECTION)

    print(f"{'='*58}")
    print(f"  DONE")
    print(f"  Employees created : {len(employees_created):,}")
    print(f"  Templates created : {templates_done:,} records")
    print(f"  Qdrant total      : {info.points_count:,} vectors (collection total)")
    print(f"  Elapsed           : {elapsed:.2f}s")
    print(f"  Throughput        : {templates_done/elapsed:,.0f} vectors/s")
    print(f"{'='*58}\n")


def main():
    ap = argparse.ArgumentParser(description="Seed OmniSight with test employees + face vectors")
    ap.add_argument("--employees", type=int, default=1000,
                    help="Number of employees to create (default: 1000)")
    ap.add_argument("--clear", action="store_true",
                    help="Delete existing EMP* employees first, then re-seed")
    args = ap.parse_args()
    asyncio.run(seed(args.employees, args.clear))


if __name__ == "__main__":
    main()
