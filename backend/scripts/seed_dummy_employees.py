"""
Seed OmniSight with dummy employee records.

This script creates employee rows only. It does not create face templates or
Qdrant vectors, so it is fast and safe for populating the Employees UI/reporting
screens with large test data.

Usage from project root:
    my_env/Scripts/python.exe backend/scripts/seed_dummy_employees.py
    my_env/Scripts/python.exe backend/scripts/seed_dummy_employees.py --employees 25000
    my_env/Scripts/python.exe backend/scripts/seed_dummy_employees.py --clear
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
import time
import uuid
from datetime import time as dtime
from pathlib import Path

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert as pg_insert

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))
os.chdir(BACKEND_DIR)

from app.db.postgres import async_session_factory  # noqa: E402
from app.models.orm import Department, Employee, Shift  # noqa: E402


DEPARTMENTS = [
    "Engineering",
    "Human Resources",
    "Finance",
    "Operations",
    "Sales",
    "Marketing",
    "IT Support",
    "Security",
    "Maintenance",
    "Management",
]

SHIFTS = [
    ("Morning", dtime(8, 0), dtime(17, 0)),
    ("Afternoon", dtime(13, 0), dtime(22, 0)),
    ("Night", dtime(22, 0), dtime(7, 0)),
]


def _bar(done: int, total: int, width: int = 30) -> str:
    if total <= 0:
        return "[##############################] 0/0"
    filled = int(width * done / total)
    return f"[{'#' * filled}{'.' * (width - filled)}] {done:>{len(str(total))}}/{total}"


async def _ensure_departments(db) -> list[int]:
    result = await db.execute(select(Department))
    existing = {d.name: d.id for d in result.scalars().all()}

    for name in DEPARTMENTS:
        if name not in existing:
            db.add(Department(name=name))

    await db.flush()
    result = await db.execute(select(Department).where(Department.name.in_(DEPARTMENTS)))
    return [dept.id for dept in result.scalars().all()]


async def _ensure_shifts(db) -> list[int]:
    result = await db.execute(select(Shift))
    existing = {s.name: s.id for s in result.scalars().all()}

    for name, start_time, end_time in SHIFTS:
        if name not in existing:
            db.add(Shift(name=name, start_time=start_time, end_time=end_time))

    await db.flush()
    result = await db.execute(select(Shift).where(Shift.name.in_([s[0] for s in SHIFTS])))
    return [shift.id for shift in result.scalars().all()]


def _employee_code(prefix: str, number: int) -> str:
    return f"{prefix}{number:05d}"


async def seed_dummy_employees(
    *,
    employees: int,
    prefix: str,
    start: int,
    batch_size: int,
    clear: bool,
) -> None:
    if employees < 1:
        raise ValueError("--employees must be at least 1")
    if start < 1:
        raise ValueError("--start must be at least 1")
    if batch_size < 1:
        raise ValueError("--batch-size must be at least 1")
    if len(prefix) > 10:
        raise ValueError("--prefix must be 10 characters or less")

    first_code = _employee_code(prefix, start)
    last_code = _employee_code(prefix, start + employees - 1)

    print("")
    print("=" * 64)
    print("  OmniSight Dummy Employee Seed")
    print(f"  Target employees : {employees:,}")
    print(f"  Code range       : {first_code} .. {last_code}")
    print("  Face templates   : not created")
    print("=" * 64)
    print("")

    t0 = time.perf_counter()

    async with async_session_factory() as db:
        async with db.begin():
            if clear:
                print(f"[!] Removing existing employees with emp_code LIKE '{prefix}%' ...")
                existing = await db.execute(
                    text("SELECT COUNT(*) FROM employees WHERE emp_code LIKE :pattern"),
                    {"pattern": f"{prefix}%"},
                )
                existing_count = existing.scalar() or 0
                await db.execute(
                    text("DELETE FROM employees WHERE emp_code LIKE :pattern"),
                    {"pattern": f"{prefix}%"},
                )
                print(f"    Deleted {existing_count:,} employees.")
                print("    Note: if those employees had face templates, run reconcile_qdrant.py later.")
                print("")

            print("-> Ensuring departments and shifts ...")
            dept_ids = await _ensure_departments(db)
            shift_ids = await _ensure_shifts(db)
            if not dept_ids or not shift_ids:
                raise RuntimeError("Could not prepare departments/shifts")
            print(f"   Departments: {len(dept_ids)} | Shifts: {len(shift_ids)}")
            print("")

            result = await db.execute(
                select(Employee.emp_code).where(Employee.emp_code.like(f"{prefix}%"))
            )
            existing_codes = {row[0] for row in result.all()}

            target_codes = [
                _employee_code(prefix, n)
                for n in range(start, start + employees)
            ]
            codes_to_create = [code for code in target_codes if code not in existing_codes]
            skipped = len(target_codes) - len(codes_to_create)

            if skipped:
                print(f"-> Existing dummy employees skipped: {skipped:,}")

            if not codes_to_create:
                print(f"[OK] All {employees:,} target employees already exist.")
                return

            print(f"[1/1] Creating {len(codes_to_create):,} employees ...")
            created = 0

            for batch_start in range(0, len(codes_to_create), batch_size):
                batch_codes = codes_to_create[batch_start:batch_start + batch_size]
                rows = []

                for offset, code in enumerate(batch_codes):
                    absolute_index = batch_start + offset
                    rows.append(
                        {
                            "id": uuid.uuid4(),
                            "emp_code": code,
                            "full_name": f"Dummy Employee {code}",
                            "dept_id": dept_ids[absolute_index % len(dept_ids)],
                            "shift_id": shift_ids[absolute_index % len(shift_ids)],
                            "is_active": True,
                        }
                    )

                stmt = (
                    pg_insert(Employee.__table__)
                    .values(rows)
                    .on_conflict_do_nothing(index_elements=["emp_code"])
                )
                result = await db.execute(stmt)
                created += result.rowcount or 0
                print(
                    f"\r  {_bar(created, len(codes_to_create))}  "
                    f"{time.perf_counter() - t0:.1f}s",
                    end="",
                    flush=True,
                )

            print(
                f"\r  {_bar(created, len(codes_to_create))}  "
                f"{time.perf_counter() - t0:.1f}s  done"
            )

    async with async_session_factory() as db:
        total = (
            await db.execute(text("SELECT COUNT(*) FROM employees"))
        ).scalar() or 0
        dummy_total = (
            await db.execute(
                text("SELECT COUNT(*) FROM employees WHERE emp_code LIKE :pattern"),
                {"pattern": f"{prefix}%"},
            )
        ).scalar() or 0

    elapsed = time.perf_counter() - t0
    print("")
    print("=" * 64)
    print("  DONE")
    print(f"  Employees created this run : {created:,}")
    print(f"  Dummy employees total      : {dummy_total:,}")
    print(f"  Employees table total      : {total:,}")
    print(f"  Elapsed                    : {elapsed:.2f}s")
    print("=" * 64)
    print("")


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed OmniSight with dummy employees")
    parser.add_argument("--employees", type=int, default=25_000)
    parser.add_argument("--prefix", default="EMP")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--batch-size", type=int, default=1_000)
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Delete existing employees matching the prefix before seeding",
    )
    args = parser.parse_args()

    asyncio.run(
        seed_dummy_employees(
            employees=args.employees,
            prefix=args.prefix,
            start=args.start,
            batch_size=args.batch_size,
            clear=args.clear,
        )
    )


if __name__ == "__main__":
    main()
