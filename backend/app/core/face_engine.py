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
    """Lazy-loaded face engine — InsightFace loads on first use."""

    def __init__(self):
        self._app = None

    def _load(self):
        try:
            from insightface.app import FaceAnalysis
            self._app = FaceAnalysis(
                name="buffalo_l",
                providers=get_best_provider(),
            )
            self._app.prepare(ctx_id=0, det_size=(640, 640))
        except ImportError:
            raise RuntimeError(
                "insightface ยังไม่ได้ติดตั้ง — "
                "รัน: pip install insightface"
            )

    @property
    def app(self):
        if self._app is None:
            self._load()
        return self._app

    def get_embeddings(self, img: np.ndarray) -> list[np.ndarray]:
        faces = self.app.get(img)
        return [f.normed_embedding for f in faces]

    def get_quality_score(self, img: np.ndarray) -> float:
        faces = self.app.get(img)
        if not faces:
            return 0.0
        return float(faces[0].det_score)

    def get_detections(self, img: np.ndarray) -> list[tuple[int, np.ndarray, list[int]]]:
        """Returns list of (tracking_id, embedding, [x1,y1,x2,y2]) tuples."""
        faces = self.app.get(img)
        results = []
        for i, face in enumerate(faces):
            bbox = [int(v) for v in face.bbox]
            results.append((i, face.normed_embedding, bbox))
        return results


face_engine = FaceEngine()


class AntiSpoofEngine:
    """
    MiniFASNet anti-spoofing — detects photo/video replay attacks.

    Model: 2.7_80x80_MiniFASNetV2.onnx (Silent-Face-Anti-Spoofing)
    Download: python backend/scripts/download_anti_spoof_model.py

    If model file is absent, available=False and check_liveness() always
    returns (True, 1.0) — system degrades gracefully, no exception raised.
    """

    MODEL_FILENAME = "2.7_80x80_MiniFASNetV2.onnx"
    INPUT_SIZE     = (80, 80)
    SCALE          = 2.7
    _MEAN = np.array([0.485, 0.456, 0.406], dtype=np.float32)
    _STD  = np.array([0.229, 0.224, 0.225], dtype=np.float32)

    def __init__(self, model_dir: str = None):
        self._session    = None
        self._model_dir  = model_dir  # set by init_anti_spoof() at startup

    def init(self, model_dir: str):
        self._model_dir = model_dir
        self._session   = None  # reset so next use re-loads from new path

    @property
    def available(self) -> bool:
        if not self._model_dir:
            return False
        return (Path(self._model_dir) / self.MODEL_FILENAME).exists()

    def _load(self):
        path = Path(self._model_dir) / self.MODEL_FILENAME
        if not path.exists():
            raise FileNotFoundError(
                f"MiniFASNet model not found at {path}. "
                "Run: python backend/scripts/download_anti_spoof_model.py"
            )
        logger.info(f"Loading MiniFASNet anti-spoof model from {path}")
        self._session = build_session(str(path))

    @property
    def session(self) -> ort.InferenceSession:
        if self._session is None:
            self._load()
        return self._session

    def _crop_face(self, img: np.ndarray, bbox: list) -> np.ndarray | None:
        """Crop face with SCALE padding — same crop strategy as the original paper."""
        x1, y1, x2, y2 = bbox
        cx = (x1 + x2) / 2.0
        cy = (y1 + y2) / 2.0
        half = max(x2 - x1, y2 - y1) * self.SCALE / 2.0
        h, w = img.shape[:2]
        x1c = max(0, int(cx - half))
        y1c = max(0, int(cy - half))
        x2c = min(w, int(cx + half))
        y2c = min(h, int(cy + half))
        crop = img[y1c:y2c, x1c:x2c]
        if crop.size == 0:
            return None
        return cv2.resize(crop, self.INPUT_SIZE)

    def _preprocess(self, face: np.ndarray) -> np.ndarray:
        """BGR uint8 [H,W,3] → float32 NCHW tensor, ImageNet-normalized."""
        x = face[:, :, ::-1].astype(np.float32) / 255.0  # BGR→RGB, scale [0,1]
        x = (x - self._MEAN) / self._STD
        return x.transpose(2, 0, 1)[np.newaxis]  # HWC → NCHW (1,3,80,80)

    def predict(self, img: np.ndarray, bbox: list) -> float:
        """
        Returns liveness score 0.0–1.0 (higher = more likely real/live face).
        Returns 1.0 if model not available (graceful pass-through).
        """
        if not self.available:
            return 1.0
        try:
            face = self._crop_face(img, bbox)
            if face is None:
                return 0.0
            inp       = self._preprocess(face)
            input_name = self.session.get_inputs()[0].name
            logits    = self.session.run(None, {input_name: inp})[0][0]  # shape (3,)
            exp       = np.exp(logits - logits.max())
            probs     = exp / exp.sum()
            return float(probs[1])  # class 1 = real/live
        except Exception as e:
            logger.warning(f"Anti-spoof predict failed: {e}")
            return 1.0  # fail-open: don't block on model errors

    def check_liveness(self, img: np.ndarray, bbox: list, threshold: float = 0.6) -> tuple[bool, float]:
        """Returns (is_live, score). If model unavailable returns (True, 1.0)."""
        score = self.predict(img, bbox)
        return score >= threshold, score


anti_spoof_engine = AntiSpoofEngine()
