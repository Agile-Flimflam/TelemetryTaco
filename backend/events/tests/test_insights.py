from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest

from events.tests.factories import make_event

INSIGHTS_NOW = datetime(2026, 10, 4, 12, 30, 45, tzinfo=UTC)


def _get_insights(client, lookback_minutes: int):
    with patch("events.selectors.events.timezone.now", return_value=INSIGHTS_NOW):
        response = client.get(f"/api/insights?lookback_minutes={lookback_minutes}")
    assert response.status_code == 200
    return response.json()


@pytest.mark.django_db
def test_insights_endpoint_zero_fills_every_minute(client):
    make_event(distinct_id="a", timestamp=INSIGHTS_NOW)
    make_event(distinct_id="b", timestamp=INSIGHTS_NOW - timedelta(seconds=30))
    make_event(distinct_id="c", timestamp=INSIGHTS_NOW - timedelta(minutes=3))
    # Outside the five-minute window on both sides.
    make_event(distinct_id="d", timestamp=INSIGHTS_NOW - timedelta(minutes=5))
    make_event(distinct_id="e", timestamp=INSIGHTS_NOW + timedelta(minutes=1))

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
