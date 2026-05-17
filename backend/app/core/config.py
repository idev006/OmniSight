from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # Database
    database_url: str = "postgresql+asyncpg://omnisight:omnisight_pass@localhost:5432/omnisight"

    # Qdrant
    qdrant_host: str = "localhost"
    qdrant_port: int = 6333
    qdrant_collection: str = "face_registry"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # JWT
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_hours: int = 8

    # Storage
    storage_path: str = "../storage/faces"

    # ONNX
    onnxruntime_provider: str = "cpu"

    # Face Engine
    min_face_quality: float = 0.75
    match_threshold: float = 0.72
    min_templates_to_activate: int = 6

    # Multi-Camera performance
    max_fps_per_camera: int = 2       # Backend-side FPS gate per camera connection
    inference_workers: int = 2         # Thread pool size for face engine (CPU-bound)

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
