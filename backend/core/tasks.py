from celery import shared_task
from core.models import Event
from django.utils import timezone
from typing import Any


@shared_task
def process_event_task(event_data: dict[str, Any]) -> None:
    """
    Celery task to process and save an event to the database.
    
    Args:
        event_data: Dictionary containing distinct_id, event_name, and properties
    """
    Event.objects.create(
        distinct_id=event_data['distinct_id'],
        event_name=event_data['event_name'],
        properties=event_data.get('properties', {}),
        timestamp=event_data.get('timestamp', timezone.now()),
    )