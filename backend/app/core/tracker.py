"""
Hungarian-algorithm IoU tracker for multi-face detection.

Replaces the previous greedy O(T×D) matcher with scipy's linear_sum_assignment
(Jonker-Volgenant / Kuhn-Munkres), which finds the globally optimal assignment
in O(T²D) — critical when ≥5 faces appear simultaneously in one frame,
where greedy matching can "steal" a detection from a better-fit track.

Flow per camera:
  frame N   → get_detections() → [(emb, bbox), ...]
            → tracker.update()  → [(track_id, emb, bbox), ...]
  frame N+1 → same face bbox overlaps (IoU ≥ MATCH_IOU_THRESHOLD) → same track_id
            → tracker.get_cached_result(track_id) → FaceResult (skip Qdrant)

Tracks expire after TRACK_EXPIRE_S seconds of not being seen.
Cached results expire after RESULT_CACHE_S seconds (forces re-identification
if the wrong person walks into the same position).
"""

from __future__ import annotations
import time
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

import numpy as np
from scipy.optimize import linear_sum_assignment

if TYPE_CHECKING:
    from app.models.schemas import FaceResult

# ── Tunables ──────────────────────────────────────────────────────────────────
MATCH_IOU_THRESHOLD = 0.30   # min IoU to accept a track-detection assignment
TRACK_EXPIRE_S      = 2.0    # seconds of inactivity before track is dropped
RESULT_CACHE_S      = 4.0    # seconds to reuse cached Qdrant result per track


def _iou(a: list[int], b: list[int]) -> float:
    ix1 = max(a[0], b[0]);  iy1 = max(a[1], b[1])
    ix2 = min(a[2], b[2]);  iy2 = min(a[3], b[3])
    inter = max(0, ix2 - ix1) * max(0, iy2 - iy1)
    if inter == 0:
        return 0.0
    union = (a[2]-a[0])*(a[3]-a[1]) + (b[2]-b[0])*(b[3]-b[1]) - inter
    return inter / union if union > 0 else 0.0


@dataclass
class _Track:
    track_id:    int
    bbox:        list[int]
    last_seen:   float = field(default_factory=time.monotonic)
    result:      "FaceResult | None" = None
    result_time: float = 0.0


class FaceTracker:
    """
    Per-camera multi-face tracker using the Hungarian (linear sum assignment)
    algorithm for globally optimal track-detection matching.

    Why Hungarian over greedy:
      Greedy: processes tracks in dict-iteration order; early tracks can claim
      detections that would be a better fit for later tracks.
      Hungarian: minimises total assignment cost across ALL track-detection
      pairs simultaneously — critical for ≥5 faces in one frame.

    Complexity: O(min(T,D)² × max(T,D)) per frame where T=tracks, D=detections.
    For typical attendance scenarios (T,D ≤ 20) this is negligible.
    """

    def __init__(self) -> None:
        self._tracks:  dict[int, _Track] = {}
        self._next_id: int = 0

    def update(
        self,
        detections: list[tuple[np.ndarray, list[int]]],
    ) -> list[tuple[int, np.ndarray, list[int]]]:
        """
        Assign each detection to a track (or create a new one).
        Returns [(track_id, embedding, bbox), ...].
        """
        now = time.monotonic()

        # Evict stale tracks
        self._tracks = {
            k: v for k, v in self._tracks.items()
            if now - v.last_seen < TRACK_EXPIRE_S
        }

        if not detections:
            return []

        tracks = list(self._tracks.values())

        if not tracks:
            # No existing tracks — every detection is new
            result = []
            for emb, bbox in detections:
                tid = self._next_id
                self._next_id += 1
                self._tracks[tid] = _Track(track_id=tid, bbox=bbox, last_seen=now)
                result.append((tid, emb, bbox))
            return result

        # Build IoU cost matrix  shape: (T, D)
        # Cost = 1 - IoU so that linear_sum_assignment minimises cost
        # (= maximises total IoU across all matched pairs)
        T, D = len(tracks), len(detections)
        cost = np.ones((T, D), dtype=np.float32)
        for i, track in enumerate(tracks):
            for j, (_, bbox) in enumerate(detections):
                iou = _iou(track.bbox, bbox)
                cost[i, j] = 1.0 - iou

        # Hungarian assignment — globally optimal
        row_ind, col_ind = linear_sum_assignment(cost)

        matched_det_indices: set[int] = set()
        result: list[tuple[int, np.ndarray, list[int]]] = []

        for r, c in zip(row_ind, col_ind):
            if cost[r, c] <= 1.0 - MATCH_IOU_THRESHOLD:   # IoU ≥ threshold
                track = tracks[r]
                emb, bbox = detections[c]
                track.bbox      = bbox
                track.last_seen = now
                matched_det_indices.add(c)
                result.append((track.track_id, emb, bbox))

        # Unmatched detections → new tracks
        for j, (emb, bbox) in enumerate(detections):
            if j not in matched_det_indices:
                tid = self._next_id
                self._next_id += 1
                self._tracks[tid] = _Track(track_id=tid, bbox=bbox, last_seen=now)
                result.append((tid, emb, bbox))

        return result

    def get_cached_result(self, track_id: int) -> "FaceResult | None":
        track = self._tracks.get(track_id)
        if track and track.result is not None:
            if time.monotonic() - track.result_time < RESULT_CACHE_S:
                return track.result
        return None

    def set_result(self, track_id: int, result: "FaceResult") -> None:
        track = self._tracks.get(track_id)
        if track:
            track.result      = result
            track.result_time = time.monotonic()

    def clear(self) -> None:
        self._tracks.clear()


# Keep old name as alias so any future imports don't break
SimpleTracker = FaceTracker
