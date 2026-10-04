from datetime import datetime

from django.conf import settings
from django.db.models import Count, Max, Min, Q

from core.models import Event
from core.selectors.events import EventCursor


def get_person_summary(*, distinct_id: str) -> dict:
    queryset = Event.objects.filter(distinct_id=distinct_id)

    aggregate_data = queryset.aggregate(
        first_seen=Min('timestamp'),
        last_seen=Max('timestamp'),
        event_count=Count('id')
    )

    top_events = list(
        queryset.values('event_name')
        .annotate(count=Count('id'))
        .order_by('-count', 'event_name')[:5]
    )

    return {
        "distinct_id": distinct_id,
        "first_seen": aggregate_data.get('first_seen'),
        "last_seen": aggregate_data.get('last_seen'),
        "event_count": aggregate_data.get('event_count', 0) or 0,
        "top_events": top_events
    }


def list_person_events(*, distinct_id: str, limit: int, before: EventCursor | None = None) -> list[Event]:
    bounded_limit = min(limit, settings.MAX_EVENTS_LIMIT)
    queryset = Event.objects.filter(distinct_id=distinct_id).order_by("-timestamp", "-id")

    if before is not None:
        before_timestamp, before_id = before
        if before_id is None:
            queryset = queryset.filter(timestamp__lt=before_timestamp)
        else:
            queryset = queryset.filter(
                Q(timestamp__lt=before_timestamp) | Q(timestamp=before_timestamp, id__lt=before_id)
            )

    return list(queryset[:bounded_limit])
