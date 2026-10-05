from datetime import timedelta

import pytest
from django.utils import timezone

from events.models import Event
from events.tests.factories import make_event


@pytest.mark.django_db
def test_stats_endpoint_summarizes_last_24_hours(client):
    now = timezone.now()
    make_event(timestamp=now)
    make_event(timestamp=now - timedelta(hours=1))
    make_event(distinct_id="user-2", event_name="signup", timestamp=now - timedelta(hours=2))
    make_event(distinct_id="user-3", timestamp=now - timedelta(hours=30))
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
