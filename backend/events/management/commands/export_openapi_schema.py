import json
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from config.api import api


class Command(BaseCommand):
    help = "Export the Ninja OpenAPI schema to a JSON file."

    def add_arguments(self, parser) -> None:
        parser.add_argument("output", type=str, help="Path to write the schema JSON to.")

    def handle(self, *args: Any, **options: Any) -> None:
        output_path = Path(options["output"]).resolve()
        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            schema = api.get_openapi_schema()
            output_path.write_text(json.dumps(schema, indent=2), encoding="utf-8")
        except Exception as exc:  # pragma: no cover - surfaced to command caller
            raise CommandError(f"Failed to export schema: {exc}") from exc

        self.stdout.write(self.style.SUCCESS(f"Exported OpenAPI schema to {output_path}"))
