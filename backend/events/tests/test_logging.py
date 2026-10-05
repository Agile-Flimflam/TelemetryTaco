import json
import logging

import pytest

from config.logging import JsonFormatter, TextFormatter
from events.tasks import process_event_batch_task


def _record(**extra: object) -> logging.LogRecord:
    record = logging.LogRecord(
        "events.test", logging.INFO, __file__, 1, "something_happened", None, None
    )
    for key, value in extra.items():
        setattr(record, key, value)
    return record


def test_text_formatter_appends_extra_fields():
    line = TextFormatter().format(_record(task_id="abc", inserted_count=3))

    assert line.endswith("INFO events.test something_happened task_id=abc inserted_count=3")


def test_json_formatter_includes_extra_fields():
    payload = json.loads(JsonFormatter().format(_record(task_id="abc", inserted_count=3)))

    assert payload["message"] == "something_happened"
    assert payload["level"] == "INFO"
    assert payload["logger"] == "events.test"
    assert payload["task_id"] == "abc"
    assert payload["inserted_count"] == 3


def test_formatters_leave_out_celery_task_data():
    record = _record(data={"args": "([{'properties': {'email': 'a@example.com'}}],)"})

    assert "data" not in json.loads(JsonFormatter().format(record))
    assert "example.com" not in TextFormatter().format(record)


@pytest.mark.django_db
def test_batch_task_logs_its_counts(caplog):
    events_data = [
        {
            "distinct_id": "u1",
            "event_name": "signup",
            "event_uuid": "7d3d6c1e-1b0e-4c39-9d8e-2f4f0a6c0b11",
        }
    ]

    with caplog.at_level(logging.INFO, logger="events"):
        process_event_batch_task.run(events_data)

    record = next(r for r in caplog.records if r.getMessage() == "processed_event_batch")
    payload = json.loads(JsonFormatter().format(record))
    assert payload["received_count"] == 1
    assert payload["inserted_count"] == 1
