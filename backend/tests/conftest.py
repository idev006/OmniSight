"""
Shared pytest fixtures for OmniSight test suite.

Markers:
  @pytest.mark.unit        — pure Python, no DB/network (fast, always run)
  @pytest.mark.integration — requires running backend at localhost:8000
                             Run: start-dev.bat, then pytest -m integration

Usage:
  pytest -m unit                     # fast unit tests only
  pytest -m integration              # integration tests (backend must be up)
  pytest                             # all tests
  pytest --cov=app --cov-report=html # with coverage report
"""

import pytest
import httpx


# ── Integration test helpers ───────────────────────────────────────────────────

BACKEND_URL = "http://localhost:8000"


def backend_is_running() -> bool:
    """Check whether the dev backend is reachable (for integration skip logic)."""
    try:
        httpx.get(f"{BACKEND_URL}/health", timeout=2.0)
        return True
    except Exception:
        return False


requires_backend = pytest.mark.skipif(
    not backend_is_running(),
    reason="Backend not running — start start-dev.bat first",
)


@pytest.fixture(scope="module")
async def client():
    """Async HTTP client pointed at the running backend."""
    async with httpx.AsyncClient(base_url=BACKEND_URL, timeout=10.0) as c:
        yield c


@pytest.fixture(scope="module")
async def admin_token(client: httpx.AsyncClient) -> str:
    """Obtain an admin JWT (requires backend + seeded admin user)."""
    resp = await client.post(
        "/api/v1/auth/login",
        json={"username": "admin", "password": "admin"},
    )
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


@pytest.fixture(scope="module")
async def admin_headers(admin_token: str) -> dict:
    return {"Authorization": f"Bearer {admin_token}"}
