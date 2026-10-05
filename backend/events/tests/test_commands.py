from io import StringIO

import pytest
from django.core.management import call_command

from events.models import Event


@pytest.mark.django_db
def test_check_db_reports_successful_connection():
    stdout = StringIO()

    call_command("check_db", stdout=stdout)

    assert "Database connection OK" in stdout.getvalue()


@pytest.mark.django_db
def test_seed_events_creates_requested_count():
    call_command("seed_events", count=25, stdout=StringIO())

    assert Event.objects.count() == 25


@pytest.mark.django_db
def test_seed_events_if_empty_skips_a_seeded_database():
    call_command("seed_events", count=5, stdout=StringIO())
    stdout = StringIO()

    call_command("seed_events", count=5, if_empty=True, stdout=stdout)

    assert Event.objects.count() == 5
    assert "skipping" in stdout.getvalue()


@pytest.mark.django_db
def test_seed_events_if_empty_seeds_an_empty_database():
    call_command("seed_events", count=5, if_empty=True, stdout=StringIO())

    assert Event.objects.count() == 5
