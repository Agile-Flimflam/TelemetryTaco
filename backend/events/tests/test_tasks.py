from datetime import date, timedelta
from uuid import uuid4

import pytest
from django.utils import timezone

from events.models import Event
from events.tasks import process_event_batch_task


@pytest.mark.django_db
def test_process_event_batch_task_ignores_duplicate_event_uuids():
    event_uuid = str(uuid4())
    payload = [
        {
            "distinct_id": "user-123",
            "event_name": "page_view",
            "event_uuid": event_uuid,
            "timestamp": timezone.now().isoformat(),
        },
        {
            "distinct_id": "user-123",
            "event_name": "page_view",
            "event_uuid": event_uuid,
            "timestamp": (timezone.now() - timedelta(minutes=1)).isoformat(),
        },
    ]

    inserted_count = process_event_batch_task.run(payload)

    assert inserted_count == 1
    assert Event.objects.count() == 1


@pytest.mark.django_db
def test_process_event_batch_task_counts_only_newly_inserted_events():
    existing_uuid = str(uuid4())
    Event.objects.create(distinct_id="user-1", event_name="page_view", uuid=existing_uuid)
    payload = [
        {"distinct_id": "user-1", "event_name": "page_view", "event_uuid": existing_uuid},
        {"distinct_id": "user-2", "event_name": "page_view", "event_uuid": str(uuid4())},
    ]

    first_run = process_event_batch_task.run(payload)
    # A Celery retry delivers the same batch again.
    retried_run = process_event_batch_task.run(payload)

    assert first_run == 1
    assert retried_run == 0
    assert Event.objects.count() == 2


@pytest.mark.django_db
def test_process_event_batch_task_persists_single_event():
    event_uuid = str(uuid4())

    processed_count = process_event_batch_task.run(
        [
            {
                "distinct_id": "user-456",
                "event_name": "checkout_success",
                "event_uuid": event_uuid,
                "properties": {"total": 42},
                "timestamp": timezone.now().isoformat(),
            }
        ]
    )

    assert processed_count == 1
    stored_event = Event.objects.get()
    assert stored_event.distinct_id == "user-456"
    assert stored_event.event_name == "checkout_success"
    assert stored_event.properties == {"total": 42}
    assert str(stored_event.uuid) == event_uuid


@pytest.mark.django_db
def test_process_event_batch_task_converts_date_timestamp_to_start_of_day():
    event_uuid = str(uuid4())
    event_date = date(2026, 1, 1)

    process_event_batch_task.run(
        [
            {
                "distinct_id": "user-789",
                "event_name": "daily_summary",
                "event_uuid": event_uuid,
                "timestamp": event_date,
            }
        ]
    )

    stored_event = Event.objects.get()
    expected_timestamp = timezone.make_aware(
        timezone.datetime.combine(event_date, timezone.datetime.min.time()),
        timezone.get_current_timezone(),
    )
    assert stored_event.timestamp == expected_timestamp


@pytest.mark.django_db
def test_process_event_batch_task_rejects_non_datetime_isoformat_objects():
    class FakeTimestamp:
        def isoformat(self) -> str:
            return "2026-01-01"

        def __str__(self) -> str:
            return self.isoformat()

    with pytest.raises(
        ValueError,
        match="timestamp must be a datetime, date, or ISO 8601 datetime string",
    ):
        process_event_batch_task.run(
            [
                {
                    "distinct_id": "user-999",
                    "event_name": "invalid_timestamp",
                    "event_uuid": str(uuid4()),
                    "timestamp": FakeTimestamp(),
                }
            ]
        )
