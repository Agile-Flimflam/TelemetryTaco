from datetime import datetime, timedelta

from django.conf import settings
from django.utils import timezone

from events.models import Event


def purge_expired_events(*, now: datetime | None = None) -> int:
    if settings.EVENT_RETENTION_DAYS <= 0:
        return 0

    cutoff_time = (now or timezone.now()) - timedelta(days=settings.EVENT_RETENTION_DAYS)
    expired = Event.objects.filter(timestamp__lt=cutoff_time).order_by()

    # Delete in chunks so the first run against a large backlog doesn't hold one long
    # transaction and its locks; each chunk commits on its own.
    deleted_total = 0
    while True:
        chunk_ids = list(
            expired.values_list("id", flat=True)[: settings.EVENT_RETENTION_DELETE_BATCH_SIZE]
        )
        if not chunk_ids:
            return deleted_total

        deleted_count, _ = Event.objects.filter(id__in=chunk_ids).delete()
        deleted_total += deleted_count
