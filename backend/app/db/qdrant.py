from qdrant_client import AsyncQdrantClient, QdrantClient
from qdrant_client.models import (
    Distance, VectorParams, ScalarQuantization,
    ScalarQuantizationConfig, ScalarType, HnswConfigDiff,
    PayloadSchemaType,
)
from app.core.config import get_settings

settings = get_settings()

qdrant = AsyncQdrantClient(
    host=settings.qdrant_host,
    port=settings.qdrant_port,
)

_qdrant_sync: QdrantClient | None = None


def get_qdrant_sync() -> QdrantClient:
    global _qdrant_sync
    if _qdrant_sync is None:
        _qdrant_sync = QdrantClient(host=settings.qdrant_host, port=settings.qdrant_port)
    return _qdrant_sync


async def get_qdrant() -> AsyncQdrantClient:
    return qdrant

COLLECTION = settings.qdrant_collection
VECTOR_SIZE = 512


async def init_collection():
    existing = await qdrant.get_collections()
    names = [c.name for c in existing.collections]
    if COLLECTION not in names:
        await qdrant.create_collection(
            collection_name=COLLECTION,
            vectors_config=VectorParams(
                size=VECTOR_SIZE,
                distance=Distance.COSINE,
            ),
            hnsw_config=HnswConfigDiff(m=16, ef_construct=100, on_disk=False),
            quantization_config=ScalarQuantization(
                scalar=ScalarQuantizationConfig(
                    type=ScalarType.INT8,
                    always_ram=True,
                )
            ),
        )
        await qdrant.create_payload_index(
            collection_name=COLLECTION,
            field_name="dept_id",
            field_schema=PayloadSchemaType.INTEGER,
        )
