from typing import Any

from celery import shared_task
from django.utils import timezone

from core.models import Event


@shared_task
def process_event_task(event_data: dict[str, Any]) -> None:
    """
    Celery task to process and save an event to the database.

    Args:
        event_data: Dictionary containing distinct_id, event_name, and properties
    """
    # Validate required fields
    distinct_id = event_data.get("distinct_id")
    event_name = event_data.get("event_name")

    if not distinct_id:
        raise ValueError("Missing required field: 'distinct_id'")
    if not event_name:
        raise ValueError("Missing required field: 'event_name'")

    Event.objects.create(
        distinct_id=distinct_id,
        event_name=event_name,
        properties=event_data.get("properties", {}),
        timestamp=event_data.get("timestamp", timezone.now()),
    )
