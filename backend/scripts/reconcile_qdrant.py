"""
Qdrant Reconcile Script - ลบ orphaned vectors

orphaned vector = vector ที่อยู่ใน Qdrant แต่ไม่มี FaceTemplate record ใน PostgreSQL

Run:
    my_env/Scripts/python.exe backend/scripts/reconcile_qdrant.py [--yes]
"""
import asyncio
import sys
from pathlib import Path

# ให้ import app modules ได้
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from sqlalchemy import select
from qdrant_client import QdrantClient
from qdrant_client.models import PointIdsList

from app.core.config import get_settings
from app.db.postgres import async_session_factory
from app.models.orm import FaceTemplate

settings = get_settings()


async def reconcile():
    qdrant = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    collection = settings.qdrant_collection

    # ── 1. รวบรวม qdrant_ids ทั้งหมดจาก PostgreSQL ──────────────────────────
    async with async_session_factory() as db:
        result = await db.execute(select(FaceTemplate.qdrant_id))
        valid_ids = {str(row[0]) for row in result.all()}

    print(f"PostgreSQL FaceTemplate records : {len(valid_ids)}")

    # ── 2. รวบรวม point ids ทั้งหมดจาก Qdrant ───────────────────────────────
    qdrant_ids = set()
    offset = None
    while True:
        response = qdrant.scroll(
            collection_name=collection,
            limit=100,
            offset=offset,
            with_payload=False,
            with_vectors=False,
        )
        points, next_offset = response
        for p in points:
            qdrant_ids.add(str(p.id))
        if next_offset is None:
            break
        offset = next_offset

    print(f"Qdrant vectors total            : {len(qdrant_ids)}")

    # ── 3. หา orphaned ids ──────────────────────────────────────────────────
    orphaned = qdrant_ids - valid_ids
    print(f"Orphaned vectors (to delete)    : {len(orphaned)}")

    if not orphaned:
        print("Nothing to delete. Collection is clean.")
        return

    for oid in orphaned:
        print(f"  Deleting orphaned vector: {oid}")

    if "--yes" not in sys.argv:
        confirm = input(f"\nDelete {len(orphaned)} orphaned vector(s)? [y/N] ").strip().lower()
        if confirm != "y":
            print("Aborted.")
            return

    qdrant.delete(
        collection_name=collection,
        points_selector=PointIdsList(points=list(orphaned)),
    )
    print(f"Deleted {len(orphaned)} orphaned vector(s). Done.")

    # ── 4. verify ───────────────────────────────────────────────────────────
    info = qdrant.get_collection(collection)
    print(f"Qdrant vectors after cleanup    : {info.points_count}")


if __name__ == "__main__":
    asyncio.run(reconcile())
