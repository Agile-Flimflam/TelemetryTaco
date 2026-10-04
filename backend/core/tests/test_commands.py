from io import StringIO

import pytest
from django.core.management import call_command


@pytest.mark.django_db
def test_check_db_reports_successful_connection():
    stdout = StringIO()

    call_command("check_db", stdout=stdout)

    assert "Database connection OK" in stdout.getvalue()
