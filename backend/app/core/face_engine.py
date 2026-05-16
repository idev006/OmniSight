from multiprocessing import cpu_count
import onnxruntime as ort
import numpy as np


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
