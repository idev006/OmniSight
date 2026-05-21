"""
Unit tests for app.core.config

Tests: Settings defaults, lru_cache singleton behaviour, path validity.
No DB or network required — pure Python.
"""

import pytest

from app.core.config import Settings, get_settings


@pytest.mark.unit
class TestSettingsDefaults:
    def setup_method(self):
        """Use a fresh, uncached Settings instance for each test."""
        self.settings = Settings()

    def test_default_algorithm_is_hs256(self):
        assert self.settings.algorithm == "HS256"

    def test_default_expire_hours(self):
        assert self.settings.access_token_expire_hours == 8

    def test_default_inference_workers(self):
        assert self.settings.inference_workers == 4

    def test_default_max_fps_per_camera(self):
        assert self.settings.max_fps_per_camera == 2

    def test_default_match_threshold(self):
        assert self.settings.match_threshold == pytest.approx(0.72)

    def test_default_min_face_quality(self):
        assert self.settings.min_face_quality == pytest.approx(0.75)

    def test_default_min_templates(self):
        assert self.settings.min_templates_to_activate == 6

    def test_default_face_detect_size(self):
        assert self.settings.face_detect_size == 320

    def test_storage_path_is_string(self):
        assert isinstance(self.settings.storage_path, str)
        assert len(self.settings.storage_path) > 0

    def test_database_url_starts_with_postgresql(self):
        assert self.settings.database_url.startswith("postgresql")

    def test_qdrant_default_port(self):
        assert self.settings.qdrant_port == 6333

    def test_redis_url_starts_with_redis(self):
        assert self.settings.redis_url.startswith("redis://")

    def test_onnx_provider_default(self):
        assert self.settings.onnxruntime_provider == "auto"


@pytest.mark.unit
class TestSettingsCacheSingleton:
    def test_get_settings_returns_same_instance(self):
        """lru_cache must return the exact same object each call."""
        s1 = get_settings()
        s2 = get_settings()
        assert s1 is s2

    def test_settings_is_settings_instance(self):
        assert isinstance(get_settings(), Settings)
