"""
Simple IoU-based multi-face tracker.

Assigns persistent track_id across consecutive frames so the websocket scan
loop can cache Qdrant search results per track instead of searching every frame.

Flow per camera:
  frame N   → get_detections() → [(emb, bbox), ...]
            → tracker.update()  → [(track_id, emb, bbox), ...]
  frame N+1 → same face bbox overlaps (IoU ≥ 0.30) → same track_id
            → tracker.get_cached_result(track_id) → FaceResult (skip Qdrant)

Tracks expire after TRACK_EXPIRE_S seconds of not being seen.
Cached results expire after RESULT_CACHE_S seconds (forces re-identification
in case the wrong person walks into the same spot).
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np

if TYPE_CHECKING:
    from app.models.schemas import FaceResult

# ── tunables ──────────────────────────────────────────────────────────────────
MATCH_IOU_THRESHOLD = 0.30   # minimum IoU to consider same face
TRACK_EXPIRE_S      = 2.0    # seconds before an unseen track is dropped
RESULT_CACHE_S      = 4.0    # seconds to reuse a cached Qdrant result


# ── helpers ───────────────────────────────────────────────────────────────────

def _iou(a: list[int], b: list[int]) -> float:
    ix1 = max(a[0], b[0]);  iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]);  iy2 = min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    area_a = (a[2] - a[0]) * (a[3] - a[1])
    area_b = (b[2] - b[0]) * (b[3] - b[1])
    union  = area_a + area_b - inter
    return inter / union if union > 0 else 0.0


# ── data model ────────────────────────────────────────────────────────────────

@dataclass
class _Track:
    track_id:    int
    bbox:        list[int]
    last_seen:   float = field(default_factory=time.monotonic)
    result:      "FaceResult | None" = None
    result_time: float = 0.0


# ── tracker ───────────────────────────────────────────────────────────────────

class SimpleTracker:
    """One instance per camera_id, held in websocket.py._trackers."""

    def __init__(self) -> None:
        self._tracks:  dict[int, _Track] = {}
        self._next_id: int = 0

    # ── public API ────────────────────────────────────────────────────────────

    def update(
        self,
        detections: list[tuple[np.ndarray, list[int]]],
    ) -> list[tuple[int, np.ndarray, list[int]]]:
        """
        Match detections to existing tracks via IoU.
        Returns [(track_id, embedding, bbox), ...] with persistent track_ids.
        """
        now = time.monotonic()

        # drop stale tracks
        self._tracks = {
            k: v for k, v in self._tracks.items()
            if now - v.last_seen < TRACK_EXPIRE_S
        }

        unmatched = list(range(len(detections)))
        matched: list[tuple[int, int]] = []  # (track_id, det_idx)

        for track in self._tracks.values():
            best_iou, best_idx = 0.0, -1
            for idx in unmatched:
                iou = _iou(track.bbox, detections[idx][1])
                if iou > best_iou:
                    best_iou, best_idx = iou, idx
            if best_iou >= MATCH_IOU_THRESHOLD:
                track.bbox      = detections[best_idx][1]
                track.last_seen = now
                matched.append((track.track_id, best_idx))
                unmatched.remove(best_idx)

        # new tracks for unmatched detections
        for idx in unmatched:
            tid = self._next_id
            self._next_id += 1
            self._tracks[tid] = _Track(
                track_id=tid,
                bbox=detections[idx][1],
                last_seen=now,
            )
            matched.append((tid, idx))

        return [
            (tid, detections[idx][0], detections[idx][1])
            for tid, idx in matched
        ]

    def get_cached_result(self, track_id: int) -> "FaceResult | None":
        """Return cached FaceResult if still fresh, else None."""
        track = self._tracks.get(track_id)
        if track and track.result is not None:
            if time.monotonic() - track.result_time < RESULT_CACHE_S:
                return track.result
        return None

    def set_result(self, track_id: int, result: "FaceResult") -> None:
        """Store Qdrant search result against a track_id."""
        track = self._tracks.get(track_id)
        if track:
            track.result      = result
            track.result_time = time.monotonic()

    def clear(self) -> None:
        self._tracks.clear()
