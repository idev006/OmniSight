"""
Unit tests for app.core.security

Tests: password hashing, JWT round-trip, token expiry, role/permission helpers.
No DB or network required — pure Python.
"""

import time
from datetime import timedelta

import pytest
from fastapi import HTTPException
from jose import jwt

from app.core.config import get_settings
from app.core.security import (
    CurrentUser,
    create_access_token,
    decode_token,
    hash_password,
    verify_password,
)

settings = get_settings()


# ── Password hashing ──────────────────────────────────────────────────────────


@pytest.mark.unit
class TestPasswordHashing:
    def test_hash_is_different_from_plain(self):
        hashed = hash_password("secret123")
        assert hashed != "secret123"

    def test_verify_correct_password(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("correct-horse-battery-staple", hashed) is True

    def test_verify_wrong_password(self):
        hashed = hash_password("correct-horse-battery-staple")
        assert verify_password("wrong-password", hashed) is False

    def test_same_plain_produces_different_hash(self):
        """bcrypt uses random salt — two hashes of the same password differ."""
        h1 = hash_password("same")
        h2 = hash_password("same")
        assert h1 != h2
        # But both verify correctly
        assert verify_password("same", h1) is True
        assert verify_password("same", h2) is True


# ── JWT create / decode ───────────────────────────────────────────────────────


@pytest.mark.unit
class TestJWT:
    def test_create_and_decode_roundtrip(self):
        token = create_access_token(
            sub="alice",
            role="ADMIN",
            user_id="user-001",
            station_ids=["sta-aaa", "sta-bbb"],
        )
        payload = decode_token(token)
        assert payload["sub"] == "alice"
        assert payload["role"] == "ADMIN"
        assert payload["user_id"] == "user-001"
        assert payload["station_ids"] == ["sta-aaa", "sta-bbb"]

    def test_default_station_ids_empty_list(self):
        token = create_access_token(sub="bob", role="HR", user_id="user-002")
        payload = decode_token(token)
        assert payload["station_ids"] == []

    def test_custom_expire_hours(self):
        """Token created with expire_hours=1 should contain exp ~1h from now."""
        before = time.time()
        token = create_access_token(sub="charlie", role="OPERATOR", user_id="u3", expire_hours=1)
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.algorithm])
        after = time.time()
        # exp should be ~3600s from now (allow 10s clock drift)
        assert before + 3590 <= payload["exp"] <= after + 3610

    def test_invalid_token_raises_401(self):
        with pytest.raises(HTTPException) as exc_info:
            decode_token("this.is.not.a.valid.token")
        assert exc_info.value.status_code == 401

    def test_tampered_token_raises_401(self):
        token = create_access_token(sub="dave", role="HR", user_id="u4")
        # Flip a character in the signature
        tampered = token[:-4] + "xxxx"
        with pytest.raises(HTTPException) as exc_info:
            decode_token(tampered)
        assert exc_info.value.status_code == 401

    def test_wrong_secret_raises_401(self):
        """Token signed with a different key must be rejected."""
        payload = {"sub": "eve", "role": "ADMIN", "user_id": "u5", "station_ids": []}
        bad_token = jwt.encode(payload, "wrong-secret", algorithm="HS256")
        with pytest.raises(HTTPException) as exc_info:
            decode_token(bad_token)
        assert exc_info.value.status_code == 401


# ── CurrentUser role / permission helpers ─────────────────────────────────────


@pytest.mark.unit
class TestCurrentUser:
    def _make_user(self, role: str, station_ids: list[str] | None = None) -> CurrentUser:
        return CurrentUser(
            user_id="u-test",
            username="testuser",
            role=role,
            station_ids=station_ids or [],
        )

    # is_admin
    def test_admin_is_admin(self):
        assert self._make_user("ADMIN").is_admin is True

    def test_hr_is_not_admin(self):
        assert self._make_user("HR").is_admin is False

    def test_operator_is_not_admin(self):
        assert self._make_user("OPERATOR").is_admin is False

    # is_hr
    def test_admin_is_hr(self):
        assert self._make_user("ADMIN").is_hr is True

    def test_hr_is_hr(self):
        assert self._make_user("HR").is_hr is True

    def test_operator_is_not_hr(self):
        assert self._make_user("OPERATOR").is_hr is False

    # can_access_station
    def test_admin_can_access_any_station(self):
        u = self._make_user("ADMIN", station_ids=[])
        assert u.can_access_station("sta-xyz") is True

    def test_hr_can_access_any_station(self):
        u = self._make_user("HR", station_ids=[])
        assert u.can_access_station("sta-xyz") is True

    def test_operator_can_access_assigned_station(self):
        u = self._make_user("OPERATOR", station_ids=["sta-aaa", "sta-bbb"])
        assert u.can_access_station("sta-aaa") is True

    def test_operator_cannot_access_unassigned_station(self):
        u = self._make_user("OPERATOR", station_ids=["sta-aaa"])
        assert u.can_access_station("sta-bbb") is False

    def test_operator_with_no_stations_cannot_access_any(self):
        u = self._make_user("OPERATOR", station_ids=[])
        assert u.can_access_station("sta-xyz") is False
