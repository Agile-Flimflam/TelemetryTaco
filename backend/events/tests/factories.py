from datetime import datetime
from typing import Any

from django.utils import timezone

from events.models import Event


def make_event(
    *,
    distinct_id: str = "user-1",
    event_name: str = "page_view",
    timestamp: datetime | None = None,
    **fields: Any,
) -> Event:
    """Save one Event. Every field has a default, so a test names only what it's about."""
    return Event.objects.create(
        distinct_id=distinct_id,
        event_name=event_name,
        timestamp=timestamp or timezone.now(),
        **fields,
    )
