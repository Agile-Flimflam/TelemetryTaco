# sdk/AGENTS.md

Python client for TelemetryTaco. Read the root [`AGENTS.md`](../AGENTS.md) first.

## Design constraints

- **Standard library only.** `dependencies = []` in `pyproject.toml` is deliberate, so users can drop the SDK into any app. Use `urllib`, `json` and `threading`, not `requests` or `httpx`.
- **Never raise into the host application from the send path.** Network errors, HTTP errors and serialization errors are logged on the `telemetry_taco` logger, and the batch is dropped. Only misuse raises: an invalid `base_url`, or calling `capture()` after `close()`.
- **Never block the caller** unless the user chose `queue_full_policy="block"`. `capture()` only enqueues.
- **The background worker must survive any failure.** One bad batch must not stop later batches (see `test_sdk_drops_failed_request_batch_without_killing_worker`).

## How it works

`capture()` creates a `QueuedEvent` with `event_uuid` (uuid4) and `sent_at` (UTC ISO) and puts it on a bounded `queue.Queue`. The daemon worker thread collects batches of up to `batch_size`. It flushes when the batch is full, when `flush_interval` has passed, or on `flush()` / `close()`, by POSTing `{"events": [...]}` to `/api/capture/batch`. A 4xx is dropped without retry. A 5xx or network error is retried `max_retries` times with linear backoff. `_STOP` is the shutdown sentinel, and the queue-full policies must never drop it.

## Compatibility

- The wire format must match the backend's `EventCaptureSchema` (`backend/core/api/schemas.py`). Adding a field means adding it there first, as optional.
- Public API is `TelemetryTaco(...)`, `.capture()`, `.flush()`, `.close()` and the context manager. Keep keyword-only options backward compatible, and add new ones with defaults.
- Supports Python 3.11+ (`datetime.UTC` is used).

## Testing

```bash
pnpm test:sdk            # from the repo root, as CI runs it
```

That runs pytest from `sdk/` using the backend's Poetry interpreter. Running from `sdk/` matters, because the backend's Django project is also named `telemetry_taco` and would shadow the SDK elsewhere.

- Patch `urllib.request.urlopen` instead of making real requests.
- Use `_start_worker=False` to test queue behavior without a thread.
- Always `flush()` / `close()` with a `timeout` so a bug can't hang the test run.
