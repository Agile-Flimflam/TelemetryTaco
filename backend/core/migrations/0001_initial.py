# Generated migration for Event model

import uuid

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Event",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True, primary_key=True, serialize=False, verbose_name="ID"
                    ),
                ),
                (
                    "distinct_id",
                    models.CharField(db_index=True, help_text="User ID", max_length=255),
                ),
                ("event_name", models.CharField(max_length=255)),
                (
                    "properties",
                    models.JSONField(
                        blank=True,
                        default=dict,
                        help_text="Flexible JSONB field for event properties",
                    ),
                ),
                (
                    "timestamp",
                    models.DateTimeField(db_index=True, default=django.utils.timezone.now),
                ),
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        help_text="UUID for idempotency",
                        unique=True,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "db_table": "core_event",
                "ordering": ["-timestamp"],
            },
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(fields=["distinct_id", "timestamp"], name="core_event_distinc_idx"),
        ),
        migrations.AddIndex(
            model_name="event",
            index=models.Index(fields=["event_name", "timestamp"], name="core_event_event_n_idx"),
        ),
    ]
