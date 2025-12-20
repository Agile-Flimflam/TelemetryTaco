import uuid

from django.db import models
from django.utils import timezone


class Event(models.Model):
    """Event model for storing telemetry events with flexible JSONB properties."""

    distinct_id = models.CharField(max_length=255, db_index=True, help_text="User ID")
    event_name = models.CharField(max_length=255)
    properties = models.JSONField(default=dict, blank=True, help_text="Flexible JSONB field for event properties")
    timestamp = models.DateTimeField(default=timezone.now, db_index=True)
    uuid = models.UUIDField(default=uuid.uuid4, unique=True, editable=False, help_text="UUID for idempotency")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'core_event'
        indexes = [
            models.Index(fields=['distinct_id', 'timestamp']),
            models.Index(fields=['event_name', 'timestamp']),
        ]
        ordering = ['-timestamp']

    def __str__(self) -> str:
        return f"{self.event_name} - {self.distinct_id} - {self.timestamp}"
