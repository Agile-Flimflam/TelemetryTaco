# Python SDK

The SDK in `sdk/` is a small client with no dependencies beyond the standard library. It queues events in memory and sends them in batches to `POST /api/capture/batch` from a background thread, so `capture()` never waits on the network.

## Install

The SDK isn't on PyPI yet ([#37](https://github.com/Agile-Flimflam/TelemetryTaco/issues/37)). Install it from a checkout or straight from GitHub:

```bash
pip install ./sdk
pip install "telemetry-taco-sdk @ git+https://github.com/Agile-Flimflam/TelemetryTaco.git#subdirectory=sdk"
```

It needs Python 3.11 or later.

## Use

```python
from telemetry_taco import TelemetryTaco

with TelemetryTaco("http://localhost:8000") as client:
    client.capture("user-123", "feature_used", {"feature_name": "insights-refresh"})
```

The context manager sends anything still queued when it exits. For a long-lived client, create it once and call `client.close()` at shutdown. If a script exits without closing it, queued events are still sent at exit, waiting at most `exit_timeout` seconds.

`capture(distinct_id, event_name, properties=None, *, timestamp=None)` queues one event. `timestamp` defaults to now; pass one to record something that happened earlier, such as a backfill. A naive datetime is read as local time.

`flush(timeout=None)` blocks until everything queued so far has been sent or dropped. `close(timeout=None)` flushes and stops the worker thread.

The client raises in only three cases: `ValueError` from the constructor for an invalid `base_url`, `RuntimeError` from `capture()` after `close()`, and `TimeoutError` from `flush()` or `close()` when events are still unsent at the deadline. Sending happens in the background and never raises into your code.

## Options

| Option | Default | What it does |
|---|---|---|
| `base_url` | `http://localhost:8000` | The backend, without `/api`. `http://` is assumed when no scheme is given. |
| `batch_size` | 50 | Send once this many events are queued. |
| `flush_interval` | 1.0 | Otherwise, send every this many seconds while events are waiting. |
| `max_queue_size` | 1000 | Events held in memory before `queue_full_policy` applies. |
| `queue_full_policy` | `"drop_newest"` | `"drop_newest"`, `"drop_oldest"`, or `"block"`. `"block"` waits up to `request_timeout` for room, then drops the event. |
| `request_timeout` | 5.0 | Seconds per HTTP request. |
| `max_retries` | 2 | Retries after a network error or a 5xx, with a short backoff. |
| `exit_timeout` | 5.0 | Upper bound on the flush at interpreter exit, so a dead server can't hang it. |

## Delivery

- Each event gets its `event_uuid` when you call `capture()`, and keeps it across retries, so the server stores it once however many times it's sent. See [architecture.md](architecture.md#idempotency).
- Each batch is stamped with `sent_at` per attempt, so the server can correct for a wrong client clock and for time spent queued or retrying.
- A 4xx response means the server refused the batch, which retrying won't change, so the batch is dropped and logged. That includes a rate-limited request, which currently gets a 403.
- The SDK never raises from the worker thread. Dropped events and failed requests are logged to the `telemetry_taco` logger, so configure logging to see them.

## Wire format

The SDK sends exactly what `docs/api.md` describes for `POST /api/capture/batch`. `backend/events/tests/test_sdk_integration.py` runs this SDK against a live backend in CI, so a change on either side that breaks the other fails there.
