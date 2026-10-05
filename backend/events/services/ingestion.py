from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

from django.conf import settings
from django.utils import timezone

from events.services.exceptions import InvalidBatchError
from events.tasks import process_event_batch_task


@dataclass(frozen=True)
class CapturedEvent:
    """An event as the client sent it, already validated by the API schema."""

    distinct_id: str
    event_name: str
    properties: dict[str, Any] = field(default_factory=dict)
    event_uuid: UUID | None = None
    timestamp: datetime | None = None
    sent_at: datetime | None = None


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


def _normalize_event(event: CapturedEvent, *, received_at: datetime) -> NormalizedEvent:
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


def enqueue_events(events: list[CapturedEvent]) -> int:
    if not events:
        raise InvalidBatchError("events must contain at least one event")

    if len(events) > settings.MAX_CAPTURE_BATCH_SIZE:
        raise InvalidBatchError(
            f"batch size exceeds maximum of {settings.MAX_CAPTURE_BATCH_SIZE} events"
        )

    received_at = timezone.now()
    # A uuid repeated within one request is the same event; only its first copy can be stored,
    # so it's only counted once. Repeats of uuids stored earlier can't be known until the worker
    # runs, so accepted still counts those.
    unique_events: dict[UUID, NormalizedEvent] = {}
    for event in events:
        normalized = _normalize_event(event, received_at=received_at)
        unique_events.setdefault(normalized.event_uuid, normalized)

    process_event_batch_task.delay([_serialize_event(event) for event in unique_events.values()])

    return len(unique_events)
