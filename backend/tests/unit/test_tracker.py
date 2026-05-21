"""
Unit tests for app.core.tracker

Tests: _iou(), FaceTracker.update() track assignment, new-track creation,
stale-track eviction, result cache hit/miss/expiry.
No DB or network required — pure Python + NumPy.
"""

import time

import numpy as np
import pytest

from app.core.tracker import (
    MATCH_IOU_THRESHOLD,
    RESULT_CACHE_S,
    TRACK_EXPIRE_S,
    FaceTracker,
    SimpleTracker,
    _iou,
)


# ── _iou() ────────────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestIoU:
    def test_identical_boxes_iou_is_one(self):
        box = [0, 0, 100, 100]
        assert _iou(box, box) == pytest.approx(1.0)

    def test_non_overlapping_boxes_iou_is_zero(self):
        a = [0, 0, 50, 50]
        b = [100, 100, 200, 200]
        assert _iou(a, b) == 0.0

    def test_touching_boxes_iou_is_zero(self):
        """Boxes that share only an edge have zero intersection area."""
        a = [0, 0, 50, 50]
        b = [50, 0, 100, 50]
        assert _iou(a, b) == 0.0

    def test_partial_overlap(self):
        # a covers [0,0,100,100] = 10000 px
        # b covers [50,50,150,150] = 10000 px
        # intersection = [50,50,100,100] = 2500 px
        # union = 10000 + 10000 - 2500 = 17500
        a = [0, 0, 100, 100]
        b = [50, 50, 150, 150]
        expected = 2500 / 17500
        assert _iou(a, b) == pytest.approx(expected, rel=1e-5)

    def test_contained_box(self):
        # inner is fully inside outer
        outer = [0, 0, 100, 100]  # area 10000
        inner = [25, 25, 75, 75]  # area 2500
        # intersection = 2500, union = 10000
        expected = 2500 / 10000
        assert _iou(outer, inner) == pytest.approx(expected, rel=1e-5)

    def test_symmetry(self):
        a = [10, 20, 80, 90]
        b = [40, 50, 120, 130]
        assert _iou(a, b) == pytest.approx(_iou(b, a), rel=1e-6)


# ── FaceTracker.update() ──────────────────────────────────────────────────────


def _emb() -> np.ndarray:
    """Return a random unit-norm 512-d embedding."""
    v = np.random.randn(512).astype(np.float32)
    return v / np.linalg.norm(v)


@pytest.mark.unit
class TestFaceTrackerUpdate:
    def test_first_frame_creates_new_tracks(self):
        tracker = FaceTracker()
        det = [(_emb(), [0, 0, 100, 100]), (_emb(), [200, 200, 300, 300])]
        results = tracker.update(det)
        assert len(results) == 2
        ids = {r[0] for r in results}
        assert len(ids) == 2  # two distinct track IDs

    def test_same_box_reuses_track(self):
        tracker = FaceTracker()
        bbox = [0, 0, 100, 100]
        emb = _emb()
        r1 = tracker.update([(emb, bbox)])
        r2 = tracker.update([(emb, bbox)])
        # Same track ID expected
        assert r1[0][0] == r2[0][0]

    def test_non_overlapping_box_creates_new_track(self):
        tracker = FaceTracker()
        r1 = tracker.update([(_emb(), [0, 0, 100, 100])])
        # Move the box far away — IoU = 0
        r2 = tracker.update([(_emb(), [500, 500, 600, 600])])
        assert r1[0][0] != r2[0][0], "Non-overlapping boxes should get different track IDs"

    def test_empty_detections_returns_empty(self):
        tracker = FaceTracker()
        tracker.update([(_emb(), [0, 0, 100, 100])])
        result = tracker.update([])
        assert result == []

    def test_track_ids_are_monotonically_increasing(self):
        tracker = FaceTracker()
        # Three distinct non-overlapping faces
        r = tracker.update(
            [
                (_emb(), [0, 0, 50, 50]),
                (_emb(), [100, 0, 150, 50]),
                (_emb(), [200, 0, 250, 50]),
            ]
        )
        ids = sorted(r[0] for r in r)
        assert ids == list(range(len(ids)))

    def test_multiple_cameras_get_independent_trackers(self):
        """Each camera should have its own FaceTracker instance."""
        t1, t2 = FaceTracker(), FaceTracker()
        bbox = [0, 0, 100, 100]
        emb = _emb()
        r1 = t1.update([(emb, bbox)])
        r2 = t2.update([(emb, bbox)])
        # Both start at ID 0 independently
        assert r1[0][0] == 0
        assert r2[0][0] == 0

    def test_stale_track_evicted(self):
        """Tracks older than TRACK_EXPIRE_S must be evicted."""
        tracker = FaceTracker()
        # Create a track
        r1 = tracker.update([(_emb(), [0, 0, 100, 100])])
        original_id = r1[0][0]

        # Age the track past the expiry threshold
        for track in tracker._tracks.values():
            track.last_seen -= TRACK_EXPIRE_S + 0.1

        # New detection at the same position — should get a NEW track ID
        r2 = tracker.update([(_emb(), [5, 5, 95, 95])])
        assert r2[0][0] != original_id, "Evicted track should not be reused"


# ── Result cache ──────────────────────────────────────────────────────────────


@pytest.mark.unit
class TestResultCache:
    def test_cache_miss_returns_none_before_set(self):
        tracker = FaceTracker()
        r = tracker.update([(_emb(), [0, 0, 100, 100])])
        tid = r[0][0]
        assert tracker.get_cached_result(tid) is None

    def test_cache_hit_after_set(self):
        tracker = FaceTracker()
        r = tracker.update([(_emb(), [0, 0, 100, 100])])
        tid = r[0][0]
        sentinel = object()  # stand-in for a FaceResult
        tracker.set_result(tid, sentinel)  # type: ignore[arg-type]
        assert tracker.get_cached_result(tid) is sentinel

    def test_cache_expires_after_ttl(self):
        tracker = FaceTracker()
        r = tracker.update([(_emb(), [0, 0, 100, 100])])
        tid = r[0][0]
        sentinel = object()
        tracker.set_result(tid, sentinel)  # type: ignore[arg-type]

        # Rewind result_time so it appears old
        tracker._tracks[tid].result_time -= RESULT_CACHE_S + 0.1
        assert tracker.get_cached_result(tid) is None, "Expired cache should return None"

    def test_cache_respects_custom_ttl(self):
        tracker = FaceTracker()
        r = tracker.update([(_emb(), [0, 0, 100, 100])])
        tid = r[0][0]
        sentinel = object()
        tracker.set_result(tid, sentinel)  # type: ignore[arg-type]

        # Age by 1s — within default 4s TTL but outside custom 0.5s TTL
        tracker._tracks[tid].result_time -= 1.0
        assert tracker.get_cached_result(tid, ttl=0.5) is None
        assert tracker.get_cached_result(tid, ttl=5.0) is sentinel

    def test_set_result_on_unknown_track_is_noop(self):
        tracker = FaceTracker()
        # Should not raise
        tracker.set_result(9999, object())  # type: ignore[arg-type]

    def test_clear_removes_all_tracks(self):
        tracker = FaceTracker()
        tracker.update([(_emb(), [0, 0, 100, 100])])
        tracker.clear()
        assert tracker._tracks == {}


# ── Alias ─────────────────────────────────────────────────────────────────────


@pytest.mark.unit
def test_simple_tracker_is_alias():
    assert SimpleTracker is FaceTracker
