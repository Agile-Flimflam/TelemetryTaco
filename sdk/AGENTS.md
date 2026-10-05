# sdk/AGENTS.md

Python client for TelemetryTaco. Read the root [`AGENTS.md`](../AGENTS.md) first.

## Design constraints

- **Standard library only.** `dependencies = []` in `pyproject.toml` is deliberate, so users can drop the SDK into any app. Use `urllib`, `json` and `threading`, not `requests` or `httpx`.
- **The background send path never raises into the host application.** Network errors, HTTP errors and serialization errors are logged on the `telemetry_taco` logger, and the batch is dropped.
- **What the public API can raise today:**
  - `ValueError` from the constructor for an invalid `base_url`.
  - `RuntimeError` from `capture()` after `close()`.
  - `TimeoutError` from `flush(timeout=...)` / `close(timeout=...)` when events are still unsent at the deadline.

  Don't add new exceptions to this list. If you change one of them, update this section and the README.
- **Never block the caller** unless the user chose `queue_full_policy="block"`. `capture()` only enqueues. Under `"block"`, it waits up to `request_timeout` for room *without* holding `_state_lock`, then logs and drops the event.
- **Queued events survive a normal interpreter exit.** The worker is a daemon thread, so `__init__` registers an `atexit` hook that calls `close(timeout=exit_timeout)` and logs instead of raising; `close()` unregisters it. Covered by a subprocess test.
- **The background worker must survive any failure.** One bad batch must not stop later batches (see `test_sdk_drops_failed_request_batch_without_killing_worker`).

## How it works

`capture()` creates a `QueuedEvent` with `event_uuid` (uuid4) and `timestamp` (UTC ISO, now unless the caller passes one), and puts it on a bounded `queue.Queue`. The daemon worker thread collects batches of up to `batch_size`. It flushes when the batch is full, when `flush_interval` has passed, or on `flush()` / `close()`, by POSTing `{"events": [...]}` to `/api/capture/batch`. A 4xx is dropped without retry. A 5xx or network error is retried `max_retries` times with linear backoff. Each attempt stamps a fresh `sent_at` so the server can correct for client clock skew. `_STOP` is the shutdown sentinel, and the queue-full policies must never drop it.

## Compatibility

- The wire format must match the backend's `EventCaptureSchema` (`backend/core/api/schemas.py`). Adding a field means adding it there first, as optional.
- Public API is `TelemetryTaco(...)`, `.capture()`, `.flush()`, `.close()` and the context manager. Keep keyword-only options backward compatible, and add new ones with defaults.
- Supports Python 3.11+ (`datetime.UTC` is used).

## Testing

```bash
pnpm test:sdk            # quick local run from the repo root
```

That runs pytest from `sdk/` using the backend's Poetry interpreter. Running from `sdk/` matters, because the backend's Django project is also named `telemetry_taco` and would shadow the SDK elsewhere.

CI is stricter: it installs the SDK into a clean venv and runs the tests against the installed package, on Python 3.11, 3.12 and 3.13. To reproduce that locally:

```bash
python -m venv /tmp/sdk-venv && /tmp/sdk-venv/bin/pip install ./sdk pytest
/tmp/sdk-venv/bin/pytest -o pythonpath= sdk/tests
```

That catches a missing file in the package, or a dependency that only exists in the backend's environment.

- Patch `urllib.request.urlopen` instead of making real requests.
- Use `_start_worker=False` to test queue behavior without a thread.
- Always `flush()` / `close()` with a `timeout` so a bug can't hang the test run.
