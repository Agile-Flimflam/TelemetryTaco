from datetime import timedelta

import pytest
from django.conf import settings as django_settings
from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.utils import timezone

from events.models import Event
from events.selectors.events import purge_expired_events
from events.tasks import purge_expired_events_task


@pytest.mark.django_db
def test_purge_expired_events_deletes_in_chunks(settings):
    settings.EVENT_RETENTION_DAYS = 30
    settings.EVENT_RETENTION_DELETE_BATCH_SIZE = 2
    expired_at = timezone.now() - timedelta(days=31)
    Event.objects.bulk_create(
        [Event(distinct_id=f"expired-{i}", event_name="page_view") for i in range(5)]
    )
    Event.objects.update(timestamp=expired_at)
    Event.objects.create(distinct_id="fresh", event_name="page_view")

    with CaptureQueriesContext(connection) as queries:
        deleted = purge_expired_events()

    delete_statements = [q for q in queries if q["sql"].upper().startswith("DELETE")]
    assert deleted == 5
    assert len(delete_statements) == 3
    assert list(Event.objects.values_list("distinct_id", flat=True)) == ["fresh"]


@pytest.mark.django_db
def test_purge_expired_events_is_disabled_by_zero_retention(settings):
    settings.EVENT_RETENTION_DAYS = 0
    Event.objects.create(
        distinct_id="ancient",
        event_name="page_view",
        timestamp=timezone.now() - timedelta(days=999),
    )

    assert purge_expired_events() == 0
    assert Event.objects.count() == 1


def test_beat_schedules_the_purge_task():
    schedule = django_settings.CELERY_BEAT_SCHEDULE["purge-expired-events"]

    assert schedule["task"] == purge_expired_events_task.name
