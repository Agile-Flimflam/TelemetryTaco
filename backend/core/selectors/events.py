from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Count, Max, Q
from django.db.models.functions import TruncMinute
from django.utils import timezone

from core.models import Event

EventCursor = tuple[datetime, int | None]


def list_recent_events(*, limit: int, before: EventCursor | None = None) -> list[Event]:
    bounded_limit = min(limit, settings.MAX_EVENTS_LIMIT)
    queryset = Event.objects.order_by("-timestamp", "-id")

    if before is not None:
        before_timestamp, before_id = before
        if before_id is None:
            queryset = queryset.filter(timestamp__lt=before_timestamp)
        else:
            queryset = queryset.filter(
                Q(timestamp__lt=before_timestamp) | Q(timestamp=before_timestamp, id__lt=before_id)
            )

    return list(queryset[:bounded_limit])


def get_insights(*, lookback_minutes: int) -> list[dict[str, int | str]]:
    bounded_lookback = min(lookback_minutes, settings.MAX_INSIGHTS_LOOKBACK_MINUTES)
    cutoff_time = timezone.now() - timedelta(minutes=bounded_lookback)

    aggregated = (
        Event.objects.filter(timestamp__gte=cutoff_time)
        .annotate(minute=TruncMinute("timestamp"))
        .values("minute")
        .annotate(count=Count("id"))
        .order_by("minute")
    )

    return [
        {
            "time": item["minute"].strftime("%H:%M"),
            "count": item["count"],
        }
        for item in aggregated
    ]


def get_event_stats(*, now: datetime | None = None) -> dict[str, int | datetime | None]:
    cutoff_time = (now or timezone.now()) - timedelta(hours=24)

    recent = Event.objects.filter(timestamp__gte=cutoff_time).aggregate(
        events=Count("id"),
        distinct_ids=Count("distinct_id", distinct=True),
    )
    last_received = Event.objects.aggregate(last=Max("created_at"))["last"]

    return {
        "events_last_24h": recent["events"],
        "unique_distinct_ids_last_24h": recent["distinct_ids"],
        "last_event_received_at": last_received,
    }


def purge_expired_events(*, now: datetime | None = None) -> int:
    if settings.EVENT_RETENTION_DAYS <= 0:
        return 0

    cutoff_time = (now or timezone.now()) - timedelta(days=settings.EVENT_RETENTION_DAYS)
    deleted_count, _ = Event.objects.filter(timestamp__lt=cutoff_time).delete()
    return deleted_count
