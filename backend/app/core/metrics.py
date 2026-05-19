"""
Prometheus metrics for OmniSight.
Scraped via GET /metrics (text/plain exposition format).

Usage (import anywhere):
    from app.core.metrics import (
        INF_DURATION, QDRANT_DURATION,
        FRAMES_RECEIVED, FRAMES_PROCESSED, FRAMES_DROPPED,
        CACHE_HITS, CACHE_MISSES,
        ACTIVE_CAMERAS, INFERENCE_WORKERS,
    )
"""
from prometheus_client import Counter, Histogram, Gauge

# ── Latency histograms ────────────────────────────────────────────────────────

INF_DURATION = Histogram(
    "omnisight_inference_duration_seconds",
    "InsightFace buffalo_l get_detections() wall time",
    buckets=[0.05, 0.1, 0.2, 0.3, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 5.0],
)

QDRANT_DURATION = Histogram(
    "omnisight_qdrant_search_duration_seconds",
    "Qdrant search_batch() wall time",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0],
)

SPOOF_DURATION = Histogram(
    "omnisight_antispoof_duration_seconds",
    "MiniFASNet predict_batch() wall time",
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5],
)

# ── Frame counters ────────────────────────────────────────────────────────────

FRAMES_RECEIVED = Counter(
    "omnisight_frames_received_total",
    "Total WebSocket frames received from all cameras",
)

FRAMES_PROCESSED = Counter(
    "omnisight_frames_processed_total",
    "Frames that passed the FPS gate and entered the pipeline",
)

FRAMES_DROPPED = Counter(
    "omnisight_frames_dropped_fps_total",
    "Frames dropped by the per-camera FPS gate",
)

# ── Face pipeline counters ────────────────────────────────────────────────────

CACHE_HITS = Counter(
    "omnisight_tracker_cache_hits_total",
    "Faces served from IoU tracker result cache (Qdrant search skipped)",
)

CACHE_MISSES = Counter(
    "omnisight_tracker_cache_misses_total",
    "Faces that required a full Qdrant search + DB lookup",
)

FACES_DETECTED = Counter(
    "omnisight_faces_detected_total",
    "Total face detections across all cameras and frames",
)

FACES_MATCHED = Counter(
    "omnisight_faces_matched_total",
    "Faces successfully matched to a registered employee",
)

FACES_UNKNOWN = Counter(
    "omnisight_faces_unknown_total",
    "Faces with no Qdrant match (unknown person)",
)

FACES_SPOOF = Counter(
    "omnisight_faces_spoof_total",
    "Faces rejected by anti-spoofing (liveness check failed)",
)

# ── Gauges ────────────────────────────────────────────────────────────────────

ACTIVE_CAMERAS = Gauge(
    "omnisight_active_cameras",
    "Number of currently connected camera WebSocket clients",
)

INFERENCE_WORKERS = Gauge(
    "omnisight_inference_workers",
    "Current ThreadPoolExecutor worker count for face inference",
)

INFLIGHT_INFERENCES = Gauge(
    "omnisight_inflight_inferences",
    "Inference calls currently running or waiting in the thread pool",
)
