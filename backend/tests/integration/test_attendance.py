"""
Integration tests for /api/v1/attendance endpoints.

Requires a running backend at localhost:8000.
Run: .\\start-dev.bat, then: pytest -m integration
"""

import pytest

from tests.conftest import requires_backend


# ── GET /api/v1/attendance ────────────────────────────────────────────────────


@requires_backend
@pytest.mark.integration
async def test_list_attendance_requires_auth(client):
    resp = await client.get("/api/v1/attendance")
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_list_attendance_returns_list(client, admin_headers):
    resp = await client.get("/api/v1/attendance", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert isinstance(data, list)


@requires_backend
@pytest.mark.integration
async def test_list_attendance_default_limit(client, admin_headers):
    """Default limit=100 — result must not exceed it."""
    resp = await client.get("/api/v1/attendance", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) <= 100


@requires_backend
@pytest.mark.integration
async def test_list_attendance_custom_limit(client, admin_headers):
    resp = await client.get("/api/v1/attendance?limit=5", headers=admin_headers)
    assert resp.status_code == 200
    assert len(resp.json()) <= 5


@requires_backend
@pytest.mark.integration
async def test_list_attendance_record_shape(client, admin_headers):
    """If records exist they must contain required keys."""
    resp = await client.get("/api/v1/attendance?limit=1", headers=admin_headers)
    assert resp.status_code == 200
    records = resp.json()
    if records:
        rec = records[0]
        for key in ("id", "employee_id", "timestamp", "confidence_score"):
            assert key in rec, f"Missing key: {key}"


@requires_backend
@pytest.mark.integration
async def test_list_attendance_date_filter(client, admin_headers):
    """Date filter must return 200 (even if no records for that date)."""
    resp = await client.get("/api/v1/attendance?date=2000-01-01", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.json() == []


# ── GET /api/v1/attendance/kpi ────────────────────────────────────────────────


@requires_backend
@pytest.mark.integration
async def test_kpi_requires_auth(client):
    resp = await client.get("/api/v1/attendance/kpi")
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_kpi_structure(client, admin_headers):
    resp = await client.get("/api/v1/attendance/kpi", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "date" in data
    assert "today" in data
    assert "weekly" in data
    assert "by_dept" in data


@requires_backend
@pytest.mark.integration
async def test_kpi_today_counts_non_negative(client, admin_headers):
    resp = await client.get("/api/v1/attendance/kpi", headers=admin_headers)
    today = resp.json()["today"]
    assert today["present"] >= 0
    assert today["late"] >= 0
    assert today["absent"] >= 0


@requires_backend
@pytest.mark.integration
async def test_kpi_weekly_has_7_entries(client, admin_headers):
    resp = await client.get("/api/v1/attendance/kpi", headers=admin_headers)
    weekly = resp.json()["weekly"]
    assert len(weekly) == 7
    for entry in weekly:
        assert "date" in entry
        assert "count" in entry


# ── GET /api/v1/attendance/daily-report ───────────────────────────────────────


@requires_backend
@pytest.mark.integration
async def test_daily_report_requires_auth(client):
    resp = await client.get("/api/v1/attendance/daily-report")
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_daily_report_structure(client, admin_headers):
    resp = await client.get("/api/v1/attendance/daily-report", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "date" in data
    assert "late_threshold_minutes" in data
    assert "records" in data
    assert isinstance(data["records"], list)


@requires_backend
@pytest.mark.integration
async def test_daily_report_record_status_values(client, admin_headers):
    resp = await client.get("/api/v1/attendance/daily-report", headers=admin_headers)
    records = resp.json()["records"]
    valid_statuses = {"PRESENT", "LATE", "ABSENT"}
    for r in records:
        assert r["status"] in valid_statuses, f"Invalid status: {r['status']}"


@requires_backend
@pytest.mark.integration
async def test_daily_report_with_date_param(client, admin_headers):
    """Historical date with no data returns empty records (not 404)."""
    resp = await client.get(
        "/api/v1/attendance/daily-report",
        params={"date": "2000-01-01"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["records"] == []


# ── GET /api/v1/attendance/summary ────────────────────────────────────────────


@requires_backend
@pytest.mark.integration
async def test_summary_requires_auth(client):
    resp = await client.get("/api/v1/attendance/summary")
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_summary_structure(client, admin_headers):
    resp = await client.get("/api/v1/attendance/summary", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "month" in data
    assert "total_records" in data
    assert "unique_employees" in data
    assert "by_day" in data
    assert "by_department" in data


@requires_backend
@pytest.mark.integration
async def test_summary_by_day_covers_full_month(client, admin_headers):
    """by_day must have an entry for every day in the month."""
    resp = await client.get(
        "/api/v1/attendance/summary",
        params={"month": "2026-05"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    by_day = resp.json()["by_day"]
    # May has 31 days
    assert len(by_day) == 31


@requires_backend
@pytest.mark.integration
async def test_summary_month_param_format(client, admin_headers):
    resp = await client.get(
        "/api/v1/attendance/summary",
        params={"month": "2026-01"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.json()["month"] == "2026-01"


# ── PDF endpoints ─────────────────────────────────────────────────────────────


@requires_backend
@pytest.mark.integration
async def test_daily_pdf_requires_auth(client):
    resp = await client.get("/api/v1/attendance/daily-report/pdf")
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_daily_pdf_returns_pdf(client, admin_headers):
    resp = await client.get("/api/v1/attendance/daily-report/pdf", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


@requires_backend
@pytest.mark.integration
async def test_daily_pdf_content_disposition(client, admin_headers):
    resp = await client.get("/api/v1/attendance/daily-report/pdf", headers=admin_headers)
    cd = resp.headers.get("content-disposition", "")
    assert "attachment" in cd
    assert ".pdf" in cd


@requires_backend
@pytest.mark.integration
async def test_monthly_pdf_requires_auth(client):
    resp = await client.get("/api/v1/attendance/summary/pdf")
    assert resp.status_code == 401


@requires_backend
@pytest.mark.integration
async def test_monthly_pdf_returns_pdf(client, admin_headers):
    resp = await client.get("/api/v1/attendance/summary/pdf", headers=admin_headers)
    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content[:4] == b"%PDF"


@requires_backend
@pytest.mark.integration
async def test_monthly_pdf_with_month_param(client, admin_headers):
    resp = await client.get(
        "/api/v1/attendance/summary/pdf",
        params={"month": "2026-05"},
        headers=admin_headers,
    )
    assert resp.status_code == 200
    assert resp.content[:4] == b"%PDF"
    cd = resp.headers.get("content-disposition", "")
    assert "2026-05" in cd
