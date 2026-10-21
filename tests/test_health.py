"""Tests for application health and readiness checks."""

from fastapi.testclient import TestClient


def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["app_name"] == "ContextGPT"


def test_readiness_check(client: TestClient):
    response = client.get("/health/ready")
    assert response.status_code in (200, 503)
