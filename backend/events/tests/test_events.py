from datetime import timedelta

import pytest
from django.utils import timezone

from events.tests.factories import make_event


@pytest.mark.django_db
def test_events_endpoint_caps_limit_and_supports_before_filter(client, settings):
    settings.MAX_EVENTS_LIMIT = 2
    now = timezone.now()
    newest = make_event(distinct_id="newest", timestamp=now)
    middle = make_event(
        distinct_id="middle",
        timestamp=now - timedelta(minutes=1),
    )
    oldest = make_event(
        distinct_id="oldest",
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
    older = make_event(
        distinct_id="older",
        timestamp=shared_timestamp - timedelta(minutes=1),
    )
    same_timestamp_lower_id = make_event(
        distinct_id="same-timestamp-lower-id",
        timestamp=shared_timestamp,
    )
    same_timestamp_higher_id = make_event(
        distinct_id="same-timestamp-higher-id",
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
