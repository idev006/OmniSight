r"""
Integration tests for /api/v1/auth endpoints.

Requires a running backend at localhost:8000 with seeded admin user.
Run: .\start-dev.bat, then: pytest -m integration
"""

import pytest

from tests.conftest import requires_backend


@requires_backend
@pytest.mark.integration
async def test_login_admin_returns_token(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"


@requires_backend
@pytest.mark.integration
async def test_login_wrong_password_returns_401(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "wrong_password"},
    )
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_login_unknown_user_returns_401(client):
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "no_such_user", "password": "irrelevant"},
    )
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_protected_endpoint_without_token_returns_401(client):
    resp = await client.get("/api/v1/employees")
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_protected_endpoint_with_valid_token_returns_200(client, admin_headers):
    resp = await client.get("/api/v1/employees", headers=admin_headers)
    assert resp.status_code == 200


@requires_backend
@pytest.mark.integration
async def test_protected_endpoint_with_bad_token_returns_401(client):
    resp = await client.get(
        "/api/v1/employees",
        headers={"Authorization": "Bearer this.is.not.valid"},
    )
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_me_endpoint_returns_current_user(client, admin_headers):
    resp = await client.get("/api/v1/auth/me", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data.get("username") == "admin"
    assert data.get("role") == "ADMIN"
