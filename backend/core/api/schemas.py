import json
from datetime import datetime
from typing import Any
from uuid import UUID

from django.conf import settings
from ninja import Schema
from pydantic import ConfigDict, Field, field_validator

# Matches the varchar(255) columns on Event. The worker can't recover from a DataError, so
# anything the database would reject has to be refused here, before the API returns 200.
EVENT_FIELD_MAX_LENGTH = 255


def _contains_nul(value: Any) -> bool:
    # Postgres rejects NUL in text and jsonb, so one such string would fail the whole batch.
    if isinstance(value, str):
        return "\x00" in value
    if isinstance(value, dict):
        return any(_contains_nul(key) or _contains_nul(item) for key, item in value.items())
    if isinstance(value, list):
        return any(_contains_nul(item) for item in value)
    return False


class EventCaptureSchema(Schema):
    distinct_id: str = Field(min_length=1, max_length=EVENT_FIELD_MAX_LENGTH)
    event_name: str = Field(min_length=1, max_length=EVENT_FIELD_MAX_LENGTH)
    properties: dict[str, Any] = Field(default_factory=dict)
    event_uuid: UUID | None = None
    # When the event happened, by the client's clock.
    timestamp: datetime | None = None
    # When the request left the client. With timestamp, it corrects client clock skew. Without
    # it, it's taken as the event time, which is how clients before timestamp existed used it.
    sent_at: datetime | None = None

    @field_validator("distinct_id", "event_name")
    @classmethod
    def _reject_nul_in_text(cls, value: str) -> str:
        if _contains_nul(value):
            raise ValueError("must not contain NUL characters")
        return value

    @field_validator("properties")
    @classmethod
    def _limit_properties(cls, value: dict[str, Any]) -> dict[str, Any]:
        if _contains_nul(value):
            raise ValueError("must not contain NUL characters")

        max_bytes = settings.MAX_EVENT_PROPERTIES_BYTES
        size = len(json.dumps(value, separators=(",", ":")).encode())
        if size > max_bytes:
            raise ValueError(f"serialized size {size} bytes exceeds maximum of {max_bytes} bytes")
        return value


class EventBatchCaptureSchema(Schema):
    events: list[EventCaptureSchema]


class EventResponseSchema(Schema):
    model_config = ConfigDict(from_attributes=True)

    id: int
    distinct_id: str
    event_name: str
    properties: dict[str, Any]
    timestamp: datetime
    uuid: str
    created_at: datetime

    @staticmethod
    def resolve_uuid(obj: Any) -> str:
        return str(obj.uuid)


class StatusResponse(Schema):
    status: str = "ok"


class BatchStatusResponse(StatusResponse):
    accepted: int


class InsightDataPoint(Schema):
    time: str
    count: int


class EventStatsResponse(Schema):
    events_last_24h: int
    unique_distinct_ids_last_24h: int
    last_event_received_at: datetime | None


class HealthStatusResponse(Schema):
    status: str
    database: str
    cache: str
