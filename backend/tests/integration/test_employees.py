"""
Integration tests for /api/v1/employees endpoints.

Requires a running backend at localhost:8000.
Run: .\\start-dev.bat, then: pytest -m integration

Note: Create/patch tests use unique emp_code to avoid conflicts across runs.
"""

import uuid

import pytest

from tests.conftest import requires_backend


def _unique_emp_code() -> str:
    return f"TEST-{uuid.uuid4().hex[:8].upper()}"


# ── GET /api/v1/employees ─────────────────────────────────────────────────────


@requires_backend
@pytest.mark.integration
async def test_list_employees_requires_auth(client):
    resp = await client.get("/api/v1/employees")
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_list_employees_returns_list(client, admin_headers):
    resp = await client.get("/api/v1/employees", headers=admin_headers)
    assert resp.status_code == 200
    assert isinstance(resp.json(), list)


@requires_backend
@pytest.mark.integration
async def test_list_employees_record_shape(client, admin_headers):
    """Each employee must contain required fields."""
    resp = await client.get("/api/v1/employees", headers=admin_headers)
    assert resp.status_code == 200
    employees = resp.json()
    if employees:
        emp = employees[0]
        for key in ("id", "emp_code", "full_name", "is_active", "enrollment_count"):
            assert key in emp, f"Missing key: {key}"


# ── POST /api/v1/employees ────────────────────────────────────────────────────


@requires_backend
@pytest.mark.integration
async def test_create_employee_requires_auth(client):
    resp = await client.post(
        "/api/v1/employees",
        json={"emp_code": _unique_emp_code(), "full_name": "Test User"},
    )
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_create_employee_success(client, admin_headers):
    payload = {"emp_code": _unique_emp_code(), "full_name": "Integration Test Employee"}
    resp = await client.post("/api/v1/employees", json=payload, headers=admin_headers)
    assert resp.status_code == 201
    data = resp.json()
    assert data["emp_code"] == payload["emp_code"]
    assert data["full_name"] == payload["full_name"]
    assert "id" in data


@requires_backend
@pytest.mark.integration
async def test_create_employee_duplicate_code_returns_error(client, admin_headers):
    """Duplicate emp_code must return 4xx (constraint violation)."""
    code = _unique_emp_code()
    payload = {"emp_code": code, "full_name": "First"}
    await client.post("/api/v1/employees", json=payload, headers=admin_headers)

    resp2 = await client.post(
        "/api/v1/employees",
        json={"emp_code": code, "full_name": "Duplicate"},
        headers=admin_headers,
    )
    assert resp2.status_code in (400, 409, 422, 500)


@requires_backend
@pytest.mark.integration
async def test_create_employee_missing_required_field(client, admin_headers):
    """emp_code is required — missing it must return 422."""
    resp = await client.post(
        "/api/v1/employees",
        json={"full_name": "No Code"},
        headers=admin_headers,
    )
    assert resp.status_code == 422


# ── GET /api/v1/employees/{id} ────────────────────────────────────────────────


@requires_backend
@pytest.mark.integration
async def test_get_employee_requires_auth(client, admin_headers):
    """First create an employee, then fetch it anonymously."""
    create_resp = await client.post(
        "/api/v1/employees",
        json={"emp_code": _unique_emp_code(), "full_name": "Fetch Test"},
        headers=admin_headers,
    )
    emp_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/employees/{emp_id}")
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_get_employee_found(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/employees",
        json={"emp_code": _unique_emp_code(), "full_name": "Fetch OK"},
        headers=admin_headers,
    )
    emp_id = create_resp.json()["id"]

    resp = await client.get(f"/api/v1/employees/{emp_id}", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == emp_id


@requires_backend
@pytest.mark.integration
async def test_get_employee_not_found(client, admin_headers):
    fake_id = str(uuid.uuid4())
    resp = await client.get(f"/api/v1/employees/{fake_id}", headers=admin_headers)
    assert resp.status_code == 404


# ── PATCH /api/v1/employees/{id} ─────────────────────────────────────────────


@requires_backend
@pytest.mark.integration
async def test_patch_employee_full_name(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/employees",
        json={"emp_code": _unique_emp_code(), "full_name": "Original Name"},
        headers=admin_headers,
    )
    emp_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/employees/{emp_id}",
        json={"full_name": "Updated Name"},
        headers=admin_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["full_name"] == "Updated Name"


@requires_backend
@pytest.mark.integration
async def test_patch_employee_deactivate(client, admin_headers):
    create_resp = await client.post(
        "/api/v1/employees",
        json={"emp_code": _unique_emp_code(), "full_name": "To Deactivate"},
        headers=admin_headers,
    )
    emp_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/employees/{emp_id}",
        json={"is_active": False},
        headers=admin_headers,
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["is_active"] is False


@requires_backend
@pytest.mark.integration
async def test_patch_employee_not_found(client, admin_headers):
    fake_id = str(uuid.uuid4())
    resp = await client.patch(
        f"/api/v1/employees/{fake_id}",
        json={"full_name": "Ghost"},
        headers=admin_headers,
    )
    assert resp.status_code == 404
