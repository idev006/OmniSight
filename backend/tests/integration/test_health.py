r"""
Integration tests for the /health endpoint.

Requires a running backend at localhost:8000.
Run: .\start-dev.bat, then: pytest -m integration
"""

import pytest

from tests.conftest import requires_backend


@requires_backend
@pytest.mark.integration
async def test_health_returns_200(client):
    resp = await client.get("/health")
    assert resp.status_code == 200


@requires_backend
@pytest.mark.integration
async def test_health_body_has_status_ok(client):
    resp = await client.get("/health")
    data = resp.json()
    assert data.get("status") == "ok"


@requires_backend
@pytest.mark.integration
async def test_metrics_endpoint_returns_200(client):
    """Prometheus /metrics endpoint must be reachable and return text/plain."""
    resp = await client.get("/metrics")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text/plain" in content_type


@requires_backend
@pytest.mark.integration
async def test_metrics_contains_omnisight_metric(client):
    """At least one omnisight_ metric must be present in the Prometheus output."""
    resp = await client.get("/metrics")
    assert b"omnisight_" in resp.content
