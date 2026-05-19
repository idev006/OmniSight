from pathlib import Path
from pydantic_settings import BaseSettings
from functools import lru_cache

# Resolve storage relative to project root regardless of CWD
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_STORAGE_DEFAULT = str(_PROJECT_ROOT / "storage" / "faces")


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
    storage_path: str = _STORAGE_DEFAULT

    # ONNX — "auto" = detect best (CUDA→DirectML→ROCm→CPU); or force: "cuda"/"directml"/"rocm"/"cpu"
    onnxruntime_provider: str = "auto"

    # Face Engine
    min_face_quality: float = 0.75
    match_threshold: float = 0.72
    min_templates_to_activate: int = 6

    # Multi-Camera performance
    # inference_workers tuning: ceil(N_cameras × fps × inference_sec × miss_rate)
    #   640px CPU ~0.4s: 10 cams × 2fps × 0.4 × 0.6 ≈ 5 → use 6-8
    #   320px CPU ~0.1s: 10 cams × 2fps × 0.1 × 0.6 ≈ 1 → use 4
    max_fps_per_camera: int = 2       # Backend-side FPS gate per camera connection
    inference_workers: int = 4         # Thread pool size for face engine (CPU-bound)
    # face_detect_size controls InsightFace det_size — set at startup, restart required.
    # Override via .env: FACE_DETECT_SIZE=320  (options: 160,320,640,1280)
    face_detect_size: int = 320

    # Anti-spoofing
    anti_spoof_model_dir: str = str(_PROJECT_ROOT / "models" / "anti_spoof")

    # Logging
    log_dir: str = str(_PROJECT_ROOT / "logs")

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
