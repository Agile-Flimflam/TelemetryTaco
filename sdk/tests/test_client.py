import json
import urllib.request
from datetime import UTC, datetime
from unittest.mock import patch

from telemetry_taco import TelemetryTaco
from telemetry_taco.client import _STOP, QueuedEvent


class FakeResponse:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        return None

    def read(self):
        return b"{}"


def test_sdk_flushes_batched_events():
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client = TelemetryTaco(flush_interval=60, batch_size=10)
        client.capture("user-1", "page_view", {"path": "/"})
        client.capture("user-2", "checkout_success", {"total": 42})
        client.flush(timeout=2)
        client.close(timeout=2)

    assert len(requests) == 1
    request, timeout = requests[0]
    payload = json.loads(request.data.decode("utf-8"))
    assert timeout == 5.0
    assert len(payload["events"]) == 2
    assert all("event_uuid" in event for event in payload["events"])
    assert all("sent_at" in event for event in payload["events"])
    assert all("timestamp" in event for event in payload["events"])


def test_sdk_sends_capture_timestamp_and_stamps_sent_at_when_sending():
    requests = []

    def fake_urlopen(request, timeout):
        requests.append(request)
        return FakeResponse()

    happened_at = datetime(2026, 1, 1, 12, 0, tzinfo=UTC)
    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client = TelemetryTaco(flush_interval=60, batch_size=10)
        client.capture("user-1", "backfilled", timestamp=happened_at)
        client.capture("user-1", "live")
        client.flush(timeout=2)
        client.close(timeout=2)

    backfilled, live = json.loads(requests[0].data.decode("utf-8"))["events"]
    assert datetime.fromisoformat(backfilled["timestamp"]) == happened_at
    assert backfilled["sent_at"] == live["sent_at"]
    assert datetime.fromisoformat(live["timestamp"]) <= datetime.fromisoformat(live["sent_at"])
    assert datetime.fromisoformat(backfilled["sent_at"]) > happened_at


def test_sdk_drop_oldest_policy_replaces_existing_item():
    client = TelemetryTaco(max_queue_size=1, queue_full_policy="drop_oldest", _start_worker=False)
    client._queue.put(  # type: ignore[attr-defined]
        QueuedEvent(
            distinct_id="user-1",
            event_name="page_view",
            properties={},
            event_uuid="first",
            timestamp="2026-01-01T00:00:00+0000",
        )
    )

    client._enqueue(  # type: ignore[attr-defined]
        QueuedEvent(
            distinct_id="user-2",
            event_name="signup_clicked",
            properties={},
            event_uuid="second",
            timestamp="2026-01-01T00:00:01+0000",
        )
    )

    queued = client._queue.get_nowait()  # type: ignore[attr-defined]
    client._queue.task_done()  # type: ignore[attr-defined]

    assert isinstance(queued, QueuedEvent)
    assert queued.event_uuid == "second"


def test_sdk_drop_oldest_policy_preserves_stop_sentinel():
    client = TelemetryTaco(max_queue_size=1, queue_full_policy="drop_oldest", _start_worker=False)
    client._queue.put(_STOP)  # type: ignore[arg-type]

    client._enqueue(  # type: ignore[attr-defined]
        QueuedEvent(
            distinct_id="user-2",
            event_name="signup_clicked",
            properties={},
            event_uuid="second",
            timestamp="2026-01-01T00:00:01+0000",
        )
    )

    assert client._queue.unfinished_tasks == 1  # type: ignore[attr-defined]
    queued = client._queue.get_nowait()  # type: ignore[attr-defined]
    assert queued is _STOP

    client._queue.task_done()  # type: ignore[attr-defined]
    assert client._queue.unfinished_tasks == 0  # type: ignore[attr-defined]


def test_sdk_drops_non_serializable_batch_without_killing_worker():
    requests = []

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    with patch("urllib.request.urlopen", side_effect=fake_urlopen):
        client = TelemetryTaco(flush_interval=60, batch_size=10)
        client.capture("user-1", "page_view", {"captured_at": datetime.now(UTC)})
        client.flush(timeout=2)
        client.capture("user-2", "page_view", {"path": "/health"})
        client.flush(timeout=2)
        client.close(timeout=2)

    assert len(requests) == 1
    payload = json.loads(requests[0][0].data.decode("utf-8"))
    assert payload["events"][0]["distinct_id"] == "user-2"


def test_sdk_normalizes_base_url_without_scheme():
    client = TelemetryTaco(base_url="localhost:8000", _start_worker=False)

    assert client.base_url == "http://localhost:8000"
    assert client.batch_url == "http://localhost:8000/api/capture/batch"


def test_sdk_rejects_invalid_base_url():
    try:
        TelemetryTaco(base_url="ftp://localhost:8000", _start_worker=False)
    except ValueError as exc:
        assert str(exc) == "base_url must be an absolute http:// or https:// URL"
    else:
        raise AssertionError("TelemetryTaco should reject invalid base URLs")


def test_sdk_drops_failed_request_batch_without_killing_worker():
    requests = []
    original_request = urllib.request.Request
    should_fail = True

    def fake_request(*args, **kwargs):
        nonlocal should_fail
        if should_fail:
            should_fail = False
            raise ValueError("bad request")
        return original_request(*args, **kwargs)

    def fake_urlopen(request, timeout):
        requests.append((request, timeout))
        return FakeResponse()

    with (
        patch("urllib.request.Request", side_effect=fake_request),
        patch(
            "urllib.request.urlopen",
            side_effect=fake_urlopen,
        ),
    ):
        client = TelemetryTaco(flush_interval=60, batch_size=10)
        client.capture("user-1", "page_view", {"path": "/broken"})
        client.flush(timeout=2)
        client.capture("user-2", "page_view", {"path": "/healthy"})
        client.flush(timeout=2)
        client.close(timeout=2)

    assert len(requests) == 1
    payload = json.loads(requests[0][0].data.decode("utf-8"))
    assert payload["events"][0]["distinct_id"] == "user-2"
