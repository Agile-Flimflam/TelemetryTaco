from datetime import datetime

from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django_ratelimit.decorators import ratelimit
from ninja import Router
from ninja.errors import HttpError

from core.api.schemas import (
    BatchStatusResponse,
    EventBatchCaptureSchema,
    EventCaptureSchema,
    EventResponseSchema,
    EventStatsResponse,
    HealthStatusResponse,
    InsightDataPoint,
    StatusResponse,
)
from core.selectors.events import get_event_stats, get_insights, list_recent_events
from core.services.health import get_liveness_status, get_readiness_status
from core.services.ingestion import enqueue_events

router = Router()


def _parse_before_cursor(before: str | None) -> tuple[datetime, int | None] | None:
    if before is None:
        return None

    timestamp_value = before
    before_id = None

    if "," in before:
        timestamp_candidate, id_candidate = before.rsplit(",", maxsplit=1)
        try:
            before_id = int(id_candidate)
        except ValueError as exc:
            raise HttpError(
                400,
                "before cursor must be ISO 8601 timestamp or ISO 8601 timestamp,id",
            ) from exc
        timestamp_value = timestamp_candidate

    parsed_before = parse_datetime(timestamp_value)
    if parsed_before is None:
        raise HttpError(400, "before cursor must be ISO 8601 timestamp or ISO 8601 timestamp,id")

    if timezone.is_naive(parsed_before):
        parsed_before = timezone.make_aware(parsed_before, timezone.get_current_timezone())

    return parsed_before, before_id


@router.post("/capture", response=StatusResponse)
@ratelimit(key="ip", rate=settings.RATE_LIMIT_CAPTURE_EVENT, method="POST", block=True)
def capture_event(request, event: EventCaptureSchema) -> StatusResponse:
    enqueue_events([event])
    return StatusResponse(status="ok")


@router.post("/capture/batch", response=BatchStatusResponse)
@ratelimit(key="ip", rate=settings.RATE_LIMIT_CAPTURE_EVENT, method="POST", block=True)
def capture_event_batch(request, payload: EventBatchCaptureSchema) -> BatchStatusResponse:
    accepted = enqueue_events(payload.events)
    return BatchStatusResponse(status="ok", accepted=accepted)


@router.get("/events", response=list[EventResponseSchema])
@ratelimit(key="ip", rate=settings.RATE_LIMIT_LIST_EVENTS, method="GET", block=True)
def list_events(request, limit: int = 100, before: str | None = None):
    if limit < 1:
        raise HttpError(400, "limit must be greater than zero")

    return list_recent_events(limit=limit, before=_parse_before_cursor(before))


@router.get("/insights", response=list[InsightDataPoint])
@ratelimit(key="ip", rate=settings.RATE_LIMIT_GET_INSIGHTS, method="GET", block=True)
def get_event_insights(request, lookback_minutes: int = 60):
    if lookback_minutes < 1:
        raise HttpError(400, "lookback_minutes must be greater than zero")

    return get_insights(lookback_minutes=lookback_minutes)


@router.get("/stats", response=EventStatsResponse)
@ratelimit(key="ip", rate=settings.RATE_LIMIT_GET_INSIGHTS, method="GET", block=True)
def get_stats(request):
    return get_event_stats()


@router.get("/health/live", response=HealthStatusResponse)
def liveness(request) -> HealthStatusResponse:
    return get_liveness_status()


@router.get("/health/ready", response={200: HealthStatusResponse, 503: HealthStatusResponse})
def readiness(request):
    status = get_readiness_status()
    if status.status != "ok":
        return 503, status

    return status
