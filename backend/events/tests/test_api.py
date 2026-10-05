from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest
from django.core.management import call_command
from django.utils import timezone

from events.models import Event
from events.services.health import HealthStatus


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
def test_capture_batch_counts_repeated_event_uuids_once(client):
    event_uuid = str(uuid4())
    event = {"distinct_id": "user-1", "event_name": "page_view", "event_uuid": event_uuid}

    response = client.post(
        "/api/capture/batch",
        data={"events": [event, event, {"distinct_id": "user-2", "event_name": "page_view"}]},
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
def test_capture_accepts_fields_at_the_column_limit(client):
    response = client.post(
        "/api/capture",
        data={"distinct_id": "u" * 255, "event_name": "e" * 255},
        content_type="application/json",
    )

    assert response.status_code == 200
    assert Event.objects.get().distinct_id == "u" * 255


@pytest.mark.django_db
@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("distinct_id", "u" * 256),
        ("event_name", "e" * 256),
        ("distinct_id", ""),
        ("event_name", "bad\x00name"),
    ],
)
def test_capture_rejects_values_the_database_cannot_store(client, field, value):
    payload = {"distinct_id": "user-1", "event_name": "page_view", field: value}

    response = client.post("/api/capture", data=payload, content_type="application/json")

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-1] == field
    assert Event.objects.count() == 0


@pytest.mark.django_db
def test_capture_batch_rejects_whole_batch_when_one_event_is_invalid(client):
    response = client.post(
        "/api/capture/batch",
        data={
            "events": [
                {"distinct_id": "user-1", "event_name": "page_view"},
                {"distinct_id": "u" * 256, "event_name": "page_view"},
            ]
        },
        content_type="application/json",
    )

    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"][-2:] == [1, "distinct_id"]
    assert Event.objects.count() == 0


@pytest.mark.django_db
def test_capture_rejects_oversized_properties(client, settings):
    settings.MAX_EVENT_PROPERTIES_BYTES = 64

    accepted = client.post(
        "/api/capture",
        data={"distinct_id": "user-1", "event_name": "small", "properties": {"k": "v"}},
        content_type="application/json",
    )
    rejected = client.post(
        "/api/capture",
        data={"distinct_id": "user-1", "event_name": "big", "properties": {"k": "x" * 100}},
        content_type="application/json",
    )

    assert accepted.status_code == 200
    assert rejected.status_code == 422
    assert "exceeds maximum of 64 bytes" in rejected.json()["detail"][0]["msg"]
    assert list(Event.objects.values_list("event_name", flat=True)) == ["small"]


@pytest.mark.django_db
def test_capture_rejects_nul_characters_in_properties(client):
    response = client.post(
        "/api/capture",
        data={"distinct_id": "user-1", "event_name": "page_view", "properties": {"k": ["\x00"]}},
        content_type="application/json",
    )

    assert response.status_code == 422
    assert Event.objects.count() == 0


RECEIVED_AT = datetime(2026, 10, 4, 12, 0, tzinfo=UTC)


def _capture_at_receive_time(client, **fields):
    with patch("events.services.ingestion.timezone.now", return_value=RECEIVED_AT):
        response = client.post(
            "/api/capture",
            data={"distinct_id": "user-1", "event_name": "page_view", **fields},
            content_type="application/json",
        )
    assert response.status_code == 200
    return Event.objects.get().timestamp


@pytest.mark.django_db
def test_capture_without_times_uses_receive_time(client):
    assert _capture_at_receive_time(client) == RECEIVED_AT


@pytest.mark.django_db
def test_capture_with_timestamp_only_stores_it(client):
    happened_at = RECEIVED_AT - timedelta(hours=3)

    assert _capture_at_receive_time(client, timestamp=happened_at.isoformat()) == happened_at


@pytest.mark.django_db
def test_capture_with_sent_at_only_keeps_legacy_behavior(client):
    sent_at = RECEIVED_AT - timedelta(seconds=5)

    assert _capture_at_receive_time(client, sent_at=sent_at.isoformat()) == sent_at


@pytest.mark.django_db
def test_capture_corrects_client_clock_skew_with_sent_at(client):
    # The client's clock is 2 hours fast. The event happened 30 s before the request was sent.
    client_now = RECEIVED_AT + timedelta(hours=2)
    stored = _capture_at_receive_time(
        client,
        timestamp=(client_now - timedelta(seconds=30)).isoformat(),
        sent_at=client_now.isoformat(),
    )

    assert stored == RECEIVED_AT - timedelta(seconds=30)


@pytest.mark.django_db
def test_capture_clamps_future_timestamps_to_receive_time(client):
    in_a_day = RECEIVED_AT + timedelta(days=1)
    within_slack = RECEIVED_AT + timedelta(seconds=30)

    assert _capture_at_receive_time(client, timestamp=in_a_day.isoformat()) == RECEIVED_AT
    Event.objects.all().delete()
    assert _capture_at_receive_time(client, timestamp=within_slack.isoformat()) == within_slack


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
                f"{same_timestamp_higher_id.timestamp.isoformat()},{same_timestamp_higher_id.id}"
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


INSIGHTS_NOW = datetime(2026, 10, 4, 12, 30, 45, tzinfo=UTC)


def _get_insights(client, lookback_minutes: int):
    with patch("events.selectors.events.timezone.now", return_value=INSIGHTS_NOW):
        response = client.get(f"/api/insights?lookback_minutes={lookback_minutes}")
    assert response.status_code == 200
    return response.json()


@pytest.mark.django_db
def test_insights_endpoint_zero_fills_every_minute(client):
    Event.objects.create(distinct_id="a", event_name="page_view", timestamp=INSIGHTS_NOW)
    Event.objects.create(
        distinct_id="b", event_name="page_view", timestamp=INSIGHTS_NOW - timedelta(seconds=30)
    )
    Event.objects.create(
        distinct_id="c", event_name="page_view", timestamp=INSIGHTS_NOW - timedelta(minutes=3)
    )
    # Outside the five-minute window on both sides.
    Event.objects.create(
        distinct_id="d", event_name="page_view", timestamp=INSIGHTS_NOW - timedelta(minutes=5)
    )
    Event.objects.create(
        distinct_id="e", event_name="page_view", timestamp=INSIGHTS_NOW + timedelta(minutes=1)
    )

    points = _get_insights(client, 5)

    assert [point["count"] for point in points] == [0, 1, 0, 0, 2]
    assert points[0]["bucket"].startswith("2026-10-04T12:26:00")
    assert points[-1]["bucket"].startswith("2026-10-04T12:30:00")
    assert datetime.fromisoformat(points[-1]["bucket"]).utcoffset() == timedelta(0)
    assert points[-1]["time"] == "12:30"


@pytest.mark.django_db
def test_insights_endpoint_returns_one_point_per_minute_without_duplicates(client, settings):
    settings.MAX_INSIGHTS_LOOKBACK_MINUTES = 3000

    points = _get_insights(client, 1500)

    buckets = [point["bucket"] for point in points]
    assert len(points) == 1500
    assert len(set(buckets)) == 1500
    assert all(point["count"] == 0 for point in points)


@pytest.mark.django_db
def test_insights_endpoint_respects_max_lookback(client, settings):
    settings.MAX_INSIGHTS_LOOKBACK_MINUTES = 30

    assert len(_get_insights(client, 999)) == 30


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
    degraded_status = HealthStatus(status="degraded", database="error", cache="ok")

    with patch("events.api.events.get_readiness_status", return_value=degraded_status):
        response = client.get("/api/health/ready")

    assert response.status_code == 503
    assert response.json() == {
        "status": "degraded",
        "database": "error",
        "cache": "ok",
    }
