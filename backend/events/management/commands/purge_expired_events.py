from typing import Any

from django.core.management.base import BaseCommand

from events.services.retention import purge_expired_events


class Command(BaseCommand):
    help = "Delete events older than EVENT_RETENTION_DAYS."

    def handle(self, *args: Any, **options: Any) -> None:
        deleted_count = purge_expired_events()
        self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} expired events."))
