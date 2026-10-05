from datetime import UTC, datetime, timedelta
from unittest.mock import patch
from uuid import uuid4

import pytest

from events.models import Event


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
