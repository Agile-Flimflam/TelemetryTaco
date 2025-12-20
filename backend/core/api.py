from datetime import datetime, timedelta
from typing import Any

from django.db.models import Count
from django.db.models.functions import TruncMinute
from django.utils import timezone
from ninja import Router, Schema

from core.models import Event
from core.tasks import process_event_task

router = Router()


class EventSchema(Schema):
    """Pydantic schema for event capture endpoint."""
    distinct_id: str
    event_name: str
    properties: dict[str, Any] = {}


class EventResponseSchema(Schema):
    """Pydantic schema for event response."""
    id: int
    distinct_id: str
    event_name: str
    properties: dict[str, Any]
    timestamp: datetime
    uuid: str
    created_at: datetime

    @staticmethod
    def resolve_uuid(obj):
        return str(obj.uuid)


class StatusResponse(Schema):
    """Response schema for successful event capture."""
    status: str = "ok"


class InsightDataPoint(Schema):
    """Schema for a single insight data point."""
    time: str
    count: int


@router.post("/capture", response=StatusResponse)
def capture_event(request, event: EventSchema) -> StatusResponse:
    """
    Capture event endpoint.

    Accepts event data and offloads it to Celery for async processing.
    Returns immediately with 200 OK to ensure low latency.
    """
    # Convert Pydantic model to dict for Celery task
    event_data = event.dict()

    # Offload to Celery task asynchronously
    process_event_task.delay(event_data)

    # Return immediately without waiting for DB write
    return StatusResponse(status="ok")


@router.get("/events", response=list[EventResponseSchema])
def list_events(request, limit: int = 100):
    """
    List recent events endpoint.

    Returns the most recent events ordered by timestamp (descending).
    """
    events = Event.objects.order_by('-timestamp')[:limit]
    return list(events)


@router.get("/insights", response=list[InsightDataPoint])
def get_insights(request, lookback_minutes: int = 60):
    """
    Get event insights endpoint.

    Returns aggregated event counts grouped by minute for the specified lookback period.
    Uses database-level aggregation for optimal performance.

    Args:
        lookback_minutes: Number of minutes to look back from now (default: 60)

    Returns:
        List of data points with time (HH:MM format) and count
    """
    # Calculate the cutoff time
    cutoff_time = timezone.now() - timedelta(minutes=lookback_minutes)

    # Database-level aggregation: group by minute and count events
    # This is optimized as it happens entirely in the database
    aggregated = (
        Event.objects
        .filter(timestamp__gte=cutoff_time)
        .annotate(
            minute=TruncMinute('timestamp')
        )
        .values('minute')
        .annotate(count=Count('id'))
        .order_by('minute')
    )

    # Format the results
    result = []
    for item in aggregated:
        # Format time as HH:MM
        time_str = item['minute'].strftime('%H:%M')
        result.append({
            'time': time_str,
            'count': item['count']
        })

    return result

