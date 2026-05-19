import threading
from multiprocessing import cpu_count
from pathlib import Path
import logging
import onnxruntime as ort
import numpy as np
import cv2

logger = logging.getLogger(__name__)


def get_best_provider() -> list[str]:
    available = ort.get_available_providers()
    priority = [
        "CUDAExecutionProvider",
        "DirectMLExecutionProvider",
        "ROCmExecutionProvider",
        "CPUExecutionProvider",
    ]
    for p in priority:
        if p in available:
            return [p]
    return ["CPUExecutionProvider"]


def build_session(model_path: str) -> ort.InferenceSession:
    providers = get_best_provider()
    opts = ort.SessionOptions()
    if providers[0] == "CPUExecutionProvider":
        opts.intra_op_num_threads = cpu_count()
        opts.inter_op_num_threads = 2
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
    return ort.InferenceSession(model_path, opts, providers=providers)


class FaceEngine:
    """
    Lazy-loaded InsightFace buffalo_l — thread-safe singleton.

    Thread safety: _load() is guarded by threading.Lock so that concurrent
    executor threads (e.g., 8 cameras connecting simultaneously) cannot race
    to initialise the model.  ONNX InferenceSession.run() is thread-safe by
    design, so concurrent get_detections() calls after warmup are fine.
    """

    def __init__(self):
        self._app  = None
        self._lock = threading.Lock()

    def _load(self):
        from insightface.app import FaceAnalysis
        from app.core.config import get_settings
        s = get_settings()
        det_size = (s.face_detect_size, s.face_detect_size)
        self._app = FaceAnalysis(name="buffalo_l", providers=get_best_provider())
        # ctx_id=-1  →  CPU-safe (ctx_id=0 raises on machines without CUDA)
        self._app.prepare(ctx_id=-1, det_size=det_size)
        logger.info(f"FaceEngine loaded: det_size={det_size} providers={get_best_provider()}")

    def warmup(self) -> None:
        """
        Pre-load the model at startup so the first camera connection
        does not stall for 5-10 s while buffalo_l initialises.
        Safe to call from an asyncio executor thread.
        """
        with self._lock:
            if self._app is None:
                self._load()
        # Run one blank inference to JIT-compile ONNX kernels
        blank = np.zeros((64, 64, 3), dtype=np.uint8)
        self._app.get(blank)
        logger.info("FaceEngine warm-up complete")

    @property
    def app(self):
        if self._app is None:
            with self._lock:           # double-checked locking
                if self._app is None:
                    self._load()
        return self._app

    def get_embeddings(self, img: np.ndarray) -> list[np.ndarray]:
        return [f.normed_embedding for f in self.app.get(img)]

    def get_quality_score(self, img: np.ndarray) -> float:
        faces = self.app.get(img)
        return float(faces[0].det_score) if faces else 0.0

    def get_detections(self, img: np.ndarray) -> list[tuple[int, np.ndarray, list[int]]]:
        """Returns [(index, normed_embedding, [x1,y1,x2,y2]), ...]."""
        return [
            (i, f.normed_embedding, [int(v) for v in f.bbox])
            for i, f in enumerate(self.app.get(img))
        ]


face_engine = FaceEngine()


# ── Face crop helper (module-level to avoid closure allocation per frame) ─────

def crop_face_jpeg(frame: np.ndarray, bbox: list[int], quality: int = 85) -> bytes | None:
    """Crop bbox from frame with 25% padding and encode as JPEG bytes."""
    try:
        x1, y1, x2, y2 = bbox
        ih, iw = frame.shape[:2]
        px = int((x2 - x1) * 0.25)
        py = int((y2 - y1) * 0.25)
        crop = frame[max(0, y1 - py):min(ih, y2 + py),
                     max(0, x1 - px):min(iw, x2 + px)]
        if crop.size == 0:
            return None
        ok, buf = cv2.imencode('.jpg', crop, [cv2.IMWRITE_JPEG_QUALITY, quality])
        return buf.tobytes() if ok else None
    except Exception:
        return None


class AntiSpoofEngine:
    """
    MiniFASNet V2 anti-spoofing — detects photo/video replay attacks.

    Model: 2.7_80x80_MiniFASNetV2.onnx (Silent-Face-Anti-Spoofing)
    Download: python backend/scripts/download_anti_spoof_model.py

    Thread safety: ONNX InferenceSession.run() is thread-safe.
    _load() is guarded by threading.Lock (same pattern as FaceEngine).

    Graceful degradation: if model absent → available=False →
    all liveness checks return (True, 1.0), system continues normally.
    """

    MODEL_FILENAME = "2.7_80x80_MiniFASNetV2.onnx"
    INPUT_SIZE     = (80, 80)
    SCALE          = 2.7
    _MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    _STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def __init__(self):
        self._session   = None
        self._model_dir = None
        self._lock      = threading.Lock()

    def init(self, model_dir: str) -> None:
        self._model_dir = model_dir
        self._session   = None

    @property
    def available(self) -> bool:
        return bool(self._model_dir) and (
            Path(self._model_dir) / self.MODEL_FILENAME
        ).exists()

    def _load(self) -> None:
        path = Path(self._model_dir) / self.MODEL_FILENAME
        if not path.exists():
            raise FileNotFoundError(str(path))
        logger.info(f"Loading MiniFASNet from {path}")
        self._session = build_session(str(path))

    @property
    def session(self) -> ort.InferenceSession:
        if self._session is None:
            with self._lock:
                if self._session is None:
                    self._load()
        return self._session

    # ── crop / preprocess ─────────────────────────────────────────────────────

    def _crop_face(self, img: np.ndarray, bbox: list) -> np.ndarray | None:
        x1, y1, x2, y2 = bbox
        cx, cy = (x1 + x2) / 2.0, (y1 + y2) / 2.0
        half   = max(x2 - x1, y2 - y1) * self.SCALE / 2.0
        h, w   = img.shape[:2]
        crop   = img[max(0, int(cy - half)):min(h, int(cy + half)),
                     max(0, int(cx - half)):min(w, int(cx + half))]
        return cv2.resize(crop, self.INPUT_SIZE) if crop.size else None

    def _preprocess(self, face: np.ndarray) -> np.ndarray:
        """BGR uint8 → float32 NCHW (1,3,80,80) ImageNet-normalised."""
        x = face[:, :, ::-1].astype(np.float32) / 255.0
        x = (x - self._MEAN) / self._STD
        return x.transpose(2, 0, 1)[np.newaxis]

    @staticmethod
    def _softmax_class1(logits: np.ndarray) -> float:
        exp = np.exp(logits - logits.max())
        return float((exp / exp.sum())[1])

    # ── public API ────────────────────────────────────────────────────────────

    def predict(self, img: np.ndarray, bbox: list) -> float:
        """Single-face liveness score 0–1. Returns 1.0 if model unavailable."""
        if not self.available:
            return 1.0
        try:
            face = self._crop_face(img, bbox)
            if face is None:
                return 0.0
            inp  = self._preprocess(face)
            name = self.session.get_inputs()[0].name
            logits = self.session.run(None, {name: inp})[0][0]
            return self._softmax_class1(logits)
        except Exception as e:
            logger.warning(f"Anti-spoof predict failed: {e}")
            return 1.0

    def predict_batch(self, img: np.ndarray, bboxes: list) -> list[float]:
        """
        Batch liveness scoring — N faces in ONE ONNX call.

        Input:  frame BGR + list of N bboxes [x1,y1,x2,y2]
        Output: list of N liveness scores (same order)
        Invalid crop → 0.0 | unavailable model → [1.0]*N
        """
        if not self.available or not bboxes:
            return [1.0] * len(bboxes)
        try:
            indexed: list[tuple[int, np.ndarray]] = []
            for i, bbox in enumerate(bboxes):
                crop = self._crop_face(img, bbox)
                if crop is not None:
                    indexed.append((i, self._preprocess(crop)))

            if not indexed:
                return [0.0] * len(bboxes)

            batch  = np.concatenate([t for _, t in indexed], axis=0)  # (M,3,80,80)
            name   = self.session.get_inputs()[0].name
            logits = self.session.run(None, {name: batch})[0]          # (M,3)

            scores = [0.0] * len(bboxes)
            for rank, (orig_i, _) in enumerate(indexed):
                scores[orig_i] = self._softmax_class1(logits[rank])
            return scores
        except Exception as e:
            logger.warning(f"Anti-spoof batch predict failed: {e}")
            return [1.0] * len(bboxes)

    def check_liveness(self, img: np.ndarray, bbox: list,
                       threshold: float = 0.6) -> tuple[bool, float]:
        score = self.predict(img, bbox)
        return score >= threshold, score


anti_spoof_engine = AntiSpoofEngine()
