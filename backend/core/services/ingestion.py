from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from django.conf import settings
from django.utils import timezone
from ninja.errors import HttpError

from core.api.schemas import EventCaptureSchema
from core.tasks import process_event_batch_task


@dataclass(frozen=True)
class NormalizedEvent:
    distinct_id: str
    event_name: str
    properties: dict[str, Any]
    event_uuid: UUID
    timestamp: datetime


# Clocks drift and requests take time, so allow a little slack before treating an event time as
# bogus. Anything later is clamped to the receive time so it can't sit in future insight buckets.
MAX_FUTURE_EVENT_SKEW = timedelta(minutes=1)


def _make_aware(value: datetime) -> datetime:
    if timezone.is_naive(value):
        return timezone.make_aware(value, timezone.get_current_timezone())
    return value


def _resolve_event_time(
    *, timestamp: datetime | None, sent_at: datetime | None, received_at: datetime
) -> datetime:
    if timestamp is not None and sent_at is not None:
        # The gap between timestamp and sent_at was measured on the client's clock, so it's
        # reliable even when that clock is wrong. Anchor it to the server's receive time.
        event_time = received_at - (_make_aware(sent_at) - _make_aware(timestamp))
    elif timestamp is not None:
        event_time = _make_aware(timestamp)
    elif sent_at is not None:
        event_time = _make_aware(sent_at)
    else:
        return received_at

    if event_time > received_at + MAX_FUTURE_EVENT_SKEW:
        return received_at
    return event_time


def _normalize_event(event: EventCaptureSchema, *, received_at: datetime) -> NormalizedEvent:
    return NormalizedEvent(
        distinct_id=event.distinct_id,
        event_name=event.event_name,
        properties=event.properties,
        event_uuid=event.event_uuid or uuid4(),
        timestamp=_resolve_event_time(
            timestamp=event.timestamp, sent_at=event.sent_at, received_at=received_at
        ),
    )


def _serialize_event(event: NormalizedEvent) -> dict[str, Any]:
    return {
        "distinct_id": event.distinct_id,
        "event_name": event.event_name,
        "properties": event.properties,
        "event_uuid": str(event.event_uuid),
        "timestamp": event.timestamp.isoformat(),
    }


def enqueue_events(events: list[EventCaptureSchema]) -> int:
    if not events:
        raise HttpError(400, "events must contain at least one event")

    if len(events) > settings.MAX_CAPTURE_BATCH_SIZE:
        raise HttpError(
            400,
            f"batch size exceeds maximum of {settings.MAX_CAPTURE_BATCH_SIZE} events",
        )

    received_at = timezone.now()
    normalized = [_normalize_event(event, received_at=received_at) for event in events]
    process_event_batch_task.delay([_serialize_event(event) for event in normalized])

    return len(normalized)
