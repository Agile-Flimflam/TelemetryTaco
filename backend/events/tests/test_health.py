from unittest.mock import patch

import pytest

from events.services.health import HealthStatus


@pytest.mark.django_db
def test_readiness_reports_dependency_status(client):
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert response.json()["cache"] == "ok"


@pytest.mark.django_db
def test_readiness_returns_503_when_dependencies_are_degraded(client):
    degraded_status = HealthStatus(status="degraded", database="error", cache="ok")

    with patch("events.api.events.get_readiness_status", return_value=degraded_status):
        response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "database": "error",
        "cache": "ok",
    }
