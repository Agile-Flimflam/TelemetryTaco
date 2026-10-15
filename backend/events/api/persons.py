from ninja import Router
from ninja.errors import HttpError

from events.api.events import _parse_before_cursor
from events.api.schemas import EventResponseSchema, PersonSummaryResponse
from events.selectors.persons import get_person_summary, list_person_events

router = Router()


@router.get("/{distinct_id}", response=PersonSummaryResponse)
def get_person(request, distinct_id: str):
    return get_person_summary(distinct_id=distinct_id)


@router.get("/{distinct_id}/events", response=list[EventResponseSchema])
def list_events_for_person(request, distinct_id: str, limit: int = 100, before: str | None = None):
    if limit < 1:
        raise HttpError(400, "limit must be greater than zero")

    return list_person_events(
        distinct_id=distinct_id, limit=limit, before=_parse_before_cursor(before)
    )
