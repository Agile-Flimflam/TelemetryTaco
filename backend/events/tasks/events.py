from datetime import date, datetime, time
from typing import Any
from uuid import UUID

from celery import shared_task
from celery.utils.log import get_task_logger
from django.db import OperationalError, transaction
from django.utils import timezone
from django.utils.dateparse import parse_datetime

from events.models import Event
from events.services.retention import purge_expired_events

logger = get_task_logger(__name__)


def _parse_timestamp(raw_value: Any):
    if raw_value is None:
        return timezone.now()

    if isinstance(raw_value, datetime):
        if timezone.is_naive(raw_value):
            return timezone.make_aware(raw_value, timezone.get_current_timezone())
        return raw_value

    if isinstance(raw_value, date):
        parsed = datetime.combine(raw_value, time.min)
        return timezone.make_aware(parsed, timezone.get_current_timezone())

    if not isinstance(raw_value, str):
        raise ValueError("timestamp must be a datetime, date, or ISO 8601 datetime string")

    parsed = parse_datetime(raw_value)
    if parsed is None:
        raise ValueError("timestamp must be an ISO 8601 datetime")

    if timezone.is_naive(parsed):
        return timezone.make_aware(parsed, timezone.get_current_timezone())

    return parsed


def _build_event(event_data: dict[str, Any]) -> Event:
    distinct_id = event_data.get("distinct_id")
    event_name = event_data.get("event_name")
    event_uuid = event_data.get("event_uuid") or event_data.get("uuid")

    if not distinct_id:
        raise ValueError("Missing required field: 'distinct_id'")
    if not event_name:
        raise ValueError("Missing required field: 'event_name'")
    if not event_uuid:
        raise ValueError("Missing required field: 'event_uuid'")

    return Event(
        distinct_id=distinct_id,
        event_name=event_name,
        properties=event_data.get("properties", {}),
        timestamp=_parse_timestamp(event_data.get("timestamp")),
        uuid=UUID(str(event_uuid)),
    )


def _persist_events(events_data: list[dict[str, Any]]) -> int:
    """Insert the events and return how many rows were actually written.

    bulk_create(ignore_conflicts=True) silently skips uuids that already exist, so its input
    length overcounts. Counting the batch's uuids before and after, in one transaction, gives the
    real number; a concurrent insert of the same uuid can still skew it, which only affects logs.
    """
    if not events_data:
        return 0

    events_to_create = [_build_event(event_data) for event_data in events_data]
    batch_uuids = {event.uuid for event in events_to_create}

    with transaction.atomic():
        existing_before = Event.objects.filter(uuid__in=batch_uuids).count()
        Event.objects.bulk_create(
            events_to_create,
            batch_size=len(events_to_create),
            ignore_conflicts=True,
        )
        existing_after = Event.objects.filter(uuid__in=batch_uuids).count()

    return existing_after - existing_before


@shared_task(
    bind=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def process_event_batch_task(self, events_data: list[dict[str, Any]]) -> int:
    inserted_count = _persist_events(events_data)

    logger.info(
        "processed_event_batch",
        extra={
            "task_name": self.name,
            "task_id": self.request.id,
            "received_count": len(events_data),
            "inserted_count": inserted_count,
        },
    )
    return inserted_count


@shared_task(
    bind=True,
    autoretry_for=(OperationalError,),
    retry_backoff=True,
    retry_jitter=True,
    retry_kwargs={"max_retries": 5},
)
def purge_expired_events_task(self) -> int:
    deleted_count = purge_expired_events()
    logger.info(
        "purged_expired_events",
        extra={
            "task_name": self.name,
            "task_id": self.request.id,
            "deleted_count": deleted_count,
        },
    )
    return deleted_count
