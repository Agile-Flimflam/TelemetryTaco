import random
from datetime import timedelta
from typing import Any

from django.core.management.base import BaseCommand
from django.utils import timezone
from faker import Faker

from core.models import Event

# Event name weights: page_view (60%), button_click (30%), checkout_success (5%), error (5%)
EVENT_NAMES = ["page_view", "button_click", "checkout_success", "error"]
EVENT_WEIGHTS = [0.6, 0.3, 0.05, 0.05]


class Command(BaseCommand):
    help = "Seed the database with realistic historical event data"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete all existing events before seeding",
        )
        parser.add_argument(
            "--count",
            type=int,
            default=2000,
            help="Number of events to generate (default: 2000)",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        clean = options["clean"]
        count = options["count"]

        if clean:
            self.stdout.write(self.style.WARNING("Deleting all existing events..."))
            deleted_count = Event.objects.all().delete()[0]
            self.stdout.write(self.style.SUCCESS(f"Deleted {deleted_count} existing events."))

        self.stdout.write(f"Generating {count} events...")

        fake = Faker()
        now = timezone.now()
        # Generate timestamps over the last 24 hours
        start_time = now - timedelta(hours=24)

        # Generate a pool of distinct_ids (user IDs) for more realistic data
        # Use a smaller pool so events are grouped by user
        num_users = max(50, count // 40)  # ~40 events per user on average
        distinct_ids = [fake.uuid4() for _ in range(num_users)]

        events_to_create = []
        for _ in range(count):
            # Weighted random selection of event name
            event_name = random.choices(EVENT_NAMES, weights=EVENT_WEIGHTS)[0]  # nosec B311

            # Generate random timestamp within the last 24 hours
            random_seconds = random.randint(0, 24 * 60 * 60)  # nosec B311
            timestamp = start_time + timedelta(seconds=random_seconds)

            # Generate realistic properties based on event type
            properties = self._generate_properties(fake, event_name)

            # Select a random distinct_id from the pool
            distinct_id = random.choice(distinct_ids)  # nosec B311

            events_to_create.append(
                Event(
                    distinct_id=distinct_id,
                    event_name=event_name,
                    properties=properties,
                    timestamp=timestamp,
                )
            )

        # Bulk create for performance
        Event.objects.bulk_create(events_to_create, batch_size=500)

        self.stdout.write(
            self.style.SUCCESS(f"Successfully created {count} events in the database.")
        )

    def _generate_properties(self, fake: Faker, event_name: str) -> dict[str, Any]:
        """Generate realistic properties based on event type."""
        properties: dict[str, Any] = {}

        if event_name == "page_view":
            properties = {
                "url": fake.url(),
                "path": fake.uri_path(),
                "referrer": fake.url() if random.random() > 0.3 else None,  # nosec B311
                "user_agent": fake.user_agent(),
                "viewport_width": random.randint(320, 2560),  # nosec B311
                "viewport_height": random.randint(568, 1440),  # nosec B311
            }
        elif event_name == "button_click":
            properties = {
                "button_id": fake.word(),
                "button_text": fake.sentence(nb_words=3),
                "page_url": fake.url(),
                "element_class": fake.word() if random.random() > 0.5 else None,  # nosec B311
            }
        elif event_name == "checkout_success":
            properties = {
                "order_id": fake.uuid4(),
                "total_amount": round(random.uniform(10.0, 500.0), 2),  # nosec B311
                "currency": "USD",
                "items_count": random.randint(1, 10),  # nosec B311
                "payment_method": random.choice(["credit_card", "paypal", "apple_pay"]),  # nosec B311
            }
        elif event_name == "error":
            properties = {
                "error_type": random.choice(  # nosec B311
                    ["TypeError", "ReferenceError", "NetworkError", "ValidationError"]
                ),
                "error_message": fake.sentence(),
                "stack_trace": fake.text(max_nb_chars=200) if random.random() > 0.5 else None,  # nosec B311
                "page_url": fake.url(),
                "line_number": random.randint(1, 1000) if random.random() > 0.3 else None,  # nosec B311
            }

        return properties
