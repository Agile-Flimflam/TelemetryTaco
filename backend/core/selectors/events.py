from datetime import datetime, timedelta

from django.conf import settings
from django.db.models import Count, Q
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
    # Rows are inserted in id order, so the newest id is the last event received. This uses
    # the primary-key index instead of scanning the unindexed created_at column.
    last_received = Event.objects.order_by("-id").values_list("created_at", flat=True).first()

    return {
        "events_last_24h": recent["events"],
        "unique_distinct_ids_last_24h": recent["distinct_ids"],
        "last_event_received_at": last_received,
    }


def purge_expired_events(*, now: datetime | None = None) -> int:
    if settings.EVENT_RETENTION_DAYS <= 0:
        return 0

    cutoff_time = (now or timezone.now()) - timedelta(days=settings.EVENT_RETENTION_DAYS)
    expired = Event.objects.filter(timestamp__lt=cutoff_time).order_by()

    # Delete in chunks so the first run against a large backlog doesn't hold one long
    # transaction and its locks; each chunk commits on its own.
    deleted_total = 0
    while True:
        chunk_ids = list(
            expired.values_list("id", flat=True)[: settings.EVENT_RETENTION_DELETE_BATCH_SIZE]
        )
        if not chunk_ids:
            return deleted_total

        deleted_count, _ = Event.objects.filter(id__in=chunk_ids).delete()
        deleted_total += deleted_count
