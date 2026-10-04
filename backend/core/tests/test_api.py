from datetime import timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.utils import timezone

from core.api.schemas import HealthStatusResponse
from core.models import Event


@pytest.mark.django_db
def test_capture_event_persists_event(client):
    response = client.post(
        "/api/capture",
        data={
            "distinct_id": "user-123",
            "event_name": "signup_clicked",
            "properties": {"plan": "starter"},
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    event = Event.objects.get()
    assert event.distinct_id == "user-123"
    assert event.event_name == "signup_clicked"
    assert event.properties == {"plan": "starter"}


@pytest.mark.django_db
def test_capture_event_is_idempotent_with_event_uuid(client):
    event_uuid = str(uuid4())
    payload = {
        "distinct_id": "user-123",
        "event_name": "signup_clicked",
        "event_uuid": event_uuid,
        "properties": {"plan": "starter"},
    }

    first_response = client.post("/api/capture", data=payload, content_type="application/json")
    second_response = client.post("/api/capture", data=payload, content_type="application/json")

    assert first_response.status_code == 200
    assert second_response.status_code == 200
    assert Event.objects.count() == 1
    assert str(Event.objects.get().uuid) == event_uuid


@pytest.mark.django_db
def test_capture_batch_persists_multiple_events(client):
    response = client.post(
        "/api/capture/batch",
        data={
            "events": [
                {
                    "distinct_id": "user-123",
                    "event_name": "page_view",
                    "properties": {"path": "/"},
                },
                {
                    "distinct_id": "user-456",
                    "event_name": "checkout_success",
                    "properties": {"total": 42},
                },
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "accepted": 2}
    assert Event.objects.count() == 2


@pytest.mark.django_db
def test_capture_batch_rejects_empty_batch(client):
    response = client.post(
        "/api/capture/batch",
        data={"events": []},
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "events must contain at least one event"


@pytest.mark.django_db
def test_capture_batch_rejects_oversized_batch(client, settings):
    settings.MAX_CAPTURE_BATCH_SIZE = 2
    response = client.post(
        "/api/capture/batch",
        data={
            "events": [
                {"distinct_id": "user-1", "event_name": "page_view"},
                {"distinct_id": "user-2", "event_name": "page_view"},
                {"distinct_id": "user-3", "event_name": "page_view"},
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == "batch size exceeds maximum of 2 events"


@pytest.mark.django_db
def test_events_endpoint_caps_limit_and_supports_before_filter(client, settings):
    settings.MAX_EVENTS_LIMIT = 2
    now = timezone.now()
    newest = Event.objects.create(distinct_id="newest", event_name="page_view", timestamp=now)
    middle = Event.objects.create(
        distinct_id="middle",
        event_name="page_view",
        timestamp=now - timedelta(minutes=1),
    )
    oldest = Event.objects.create(
        distinct_id="oldest",
        event_name="page_view",
        timestamp=now - timedelta(minutes=2),
    )

    limited = client.get("/api/events?limit=999")
    before_filtered = client.get(
        "/api/events",
        data={"limit": 5, "before": f"{newest.timestamp.isoformat()},{newest.id}"},
    )

    assert limited.status_code == 200
    assert len(limited.json()) == 2
    assert limited.json()[0]["id"] == newest.id
    assert before_filtered.status_code == 200
    assert [event["id"] for event in before_filtered.json()] == [middle.id, oldest.id]


@pytest.mark.django_db
def test_events_endpoint_supports_stable_cursor_for_same_timestamp_rows(client):
    shared_timestamp = timezone.now()
    older = Event.objects.create(
        distinct_id="older",
        event_name="page_view",
        timestamp=shared_timestamp - timedelta(minutes=1),
    )
    same_timestamp_lower_id = Event.objects.create(
        distinct_id="same-timestamp-lower-id",
        event_name="page_view",
        timestamp=shared_timestamp,
    )
    same_timestamp_higher_id = Event.objects.create(
        distinct_id="same-timestamp-higher-id",
        event_name="page_view",
        timestamp=shared_timestamp,
    )

    first_page = client.get("/api/events?limit=1")
    second_page = client.get(
        "/api/events",
        data={
            "limit": 5,
            "before": (
                f"{same_timestamp_higher_id.timestamp.isoformat()},"
                f"{same_timestamp_higher_id.id}"
            ),
        },
    )

    assert first_page.status_code == 200
    assert [event["id"] for event in first_page.json()] == [same_timestamp_higher_id.id]
    assert second_page.status_code == 200
    assert [event["id"] for event in second_page.json()] == [
        same_timestamp_lower_id.id,
        older.id,
    ]


@pytest.mark.django_db
def test_events_endpoint_rejects_invalid_before_cursor(client):
    response = client.get("/api/events?before=not-a-cursor")

    assert response.status_code == 400
    assert response.json()["detail"] == (
        "before cursor must be ISO 8601 timestamp or ISO 8601 timestamp,id"
    )


@pytest.mark.django_db
def test_insights_endpoint_respects_max_lookback(client, settings):
    settings.MAX_INSIGHTS_LOOKBACK_MINUTES = 30
    now = timezone.now()
    Event.objects.create(
        distinct_id="recent",
        event_name="page_view",
        timestamp=now - timedelta(minutes=10),
    )
    Event.objects.create(
        distinct_id="stale",
        event_name="page_view",
        timestamp=now - timedelta(minutes=45),
    )

    response = client.get("/api/insights?lookback_minutes=999")

    assert response.status_code == 200
    assert response.json() == [
        {"time": (now - timedelta(minutes=10)).strftime("%H:%M"), "count": 1}
    ]


@pytest.mark.django_db
def test_stats_endpoint_summarizes_last_24_hours(client):
    now = timezone.now()
    Event.objects.create(distinct_id="user-1", event_name="page_view", timestamp=now)
    Event.objects.create(
        distinct_id="user-1", event_name="page_view", timestamp=now - timedelta(hours=1)
    )
    Event.objects.create(
        distinct_id="user-2", event_name="signup", timestamp=now - timedelta(hours=2)
    )
    Event.objects.create(
        distinct_id="user-3", event_name="page_view", timestamp=now - timedelta(hours=30)
    )
    latest = Event.objects.order_by("-created_at").first()

    response = client.get("/api/stats")

    assert response.status_code == 200
    body = response.json()
    assert body["events_last_24h"] == 3
    assert body["unique_distinct_ids_last_24h"] == 2
    assert body["last_event_received_at"] is not None
    assert latest is not None
    assert body["last_event_received_at"].startswith(latest.created_at.strftime("%Y-%m-%dT%H:%M"))


@pytest.mark.django_db
def test_stats_endpoint_handles_empty_database(client):
    response = client.get("/api/stats")

    assert response.status_code == 200
    assert response.json() == {
        "events_last_24h": 0,
        "unique_distinct_ids_last_24h": 0,
        "last_event_received_at": None,
    }


@pytest.mark.django_db
def test_purge_expired_events_command_deletes_expired_rows(settings):
    settings.EVENT_RETENTION_DAYS = 30
    Event.objects.create(
        distinct_id="expired",
        event_name="page_view",
        timestamp=timezone.now() - timedelta(days=31),
    )
    Event.objects.create(
        distinct_id="fresh",
        event_name="page_view",
        timestamp=timezone.now() - timedelta(days=5),
    )

    call_command("purge_expired_events")

    assert list(Event.objects.values_list("distinct_id", flat=True)) == ["fresh"]


@pytest.mark.django_db
def test_readiness_reports_dependency_status(client):
    response = client.get("/api/health/ready")

    assert response.status_code == 200
    assert response.json()["database"] == "ok"
    assert response.json()["cache"] == "ok"


@pytest.mark.django_db
def test_readiness_returns_503_when_dependencies_are_degraded(client):
    degraded_status = HealthStatusResponse(status="degraded", database="error", cache="ok")

    with patch("core.api.events.get_readiness_status", return_value=degraded_status):
        response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "database": "error",
        "cache": "ok",
    }
