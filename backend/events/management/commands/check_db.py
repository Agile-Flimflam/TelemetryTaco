from typing import Any

from django.core.management.base import BaseCommand, CommandError
from django.db import DatabaseError, connection


class Command(BaseCommand):
    help = "Check that the configured database is reachable."

    def handle(self, *args: Any, **options: Any) -> None:
        settings_dict = connection.settings_dict
        host = settings_dict.get("HOST") or "localhost"
        port = settings_dict.get("PORT") or "default port"
        self.stdout.write(
            f"Connecting to {connection.vendor} database '{settings_dict['NAME']}' "
            f"at {host} ({port})..."
        )

        try:
            connection.ensure_connection()
            version = ".".join(str(part) for part in connection.get_database_version())
        except DatabaseError as exc:
            raise CommandError(
                f"Database connection failed: {exc}\n"
                "Make sure the database is running (docker compose up -d db) and that "
                "DATABASE_URL in backend/.env is correct."
            ) from exc

        self.stdout.write(self.style.SUCCESS(f"Database connection OK (version {version})."))
