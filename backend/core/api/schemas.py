from datetime import datetime
from typing import Any
from uuid import UUID

from ninja import Schema
from pydantic import ConfigDict, Field


class EventCaptureSchema(Schema):
    distinct_id: str
    event_name: str
    properties: dict[str, Any] = Field(default_factory=dict)
    event_uuid: UUID | None = None
    sent_at: datetime | None = None


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
