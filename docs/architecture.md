# Architecture

TelemetryTaco has four moving parts: an HTTP API, a Celery worker, a Postgres event store, and a React dashboard that reads from the API.

```text
 Python SDK / any HTTP client
            │  POST /api/capture/batch
            ▼
 ┌──────────────────────────┐   enqueue    ┌───────┐   consume    ┌───────────────┐
 │ API (Django + Ninja)     │ ───────────► │ Redis │ ───────────► │ Celery worker │
 │ validate, normalize      │              └───────┘              │ bulk_create   │
 └──────────────────────────┘                                     └───────┬───────┘
            ▲                                                              │
            │  GET /api/events, /api/insights, /api/stats                 ▼
 ┌──────────────────────────┐            reads                    ┌───────────────┐
 │ React dashboard          │ ◄────────────────────────────────── │ Postgres      │
 └──────────────────────────┘                                     └───────────────┘
```

Celery beat runs alongside the worker and schedules the hourly retention purge. Redis is both the Celery broker (database 0) and the Django cache that holds rate-limit counters (database 1).

## Ingestion

1. **Validate.** `POST /api/capture` or `/api/capture/batch` parses the body into `EventCaptureSchema`. Everything the database could reject is refused here, with a 422, before the API accepts anything: string lengths (255 for `distinct_id` and `event_name`), NUL characters, and the serialized size of `properties`. In a batch, one invalid event rejects the whole request.
2. **Normalize and enqueue.** `services/ingestion.py` checks the batch size, gives each event an `event_uuid` if the client didn't send one, resolves its time (below), drops repeats of the same `event_uuid` within the request, and calls `process_event_batch_task.delay(...)`. The API returns `accepted` and never writes to the database in the request.
3. **Persist.** The worker builds `Event` rows and calls `bulk_create(ignore_conflicts=True)`. It retries only on `OperationalError` (the database is unreachable or failed over), with backoff, up to five times.

Because step 1 has already refused anything the database would reject, step 3 doesn't lose events to bad input after the API has said yes.

### Idempotency

Every event has a UUID, and `core_event.uuid` has a unique constraint. A retried request, a retried task, or an SDK that resends a batch after a timeout all insert the same UUIDs again, and `ignore_conflicts=True` skips them. Delivery is therefore at-least-once from the client and exactly-once in the table, as long as the client reuses the UUID on retry. The SDK does: it assigns the UUID when you call `capture()`, not when it sends.

The task's log line reports both `received_count` and `inserted_count`, so duplicates show up as the difference.

### Event time

Clients send up to two times: `timestamp` (when the event happened, by the client's clock) and `sent_at` (when the request left the client, by the same clock).

- With both, the server keeps the gap between them, which is accurate even when the client's clock is wrong, and subtracts it from its own receive time.
- With only `timestamp`, it's stored as is. With only `sent_at`, it's used as the event time, which is how clients behaved before `timestamp` existed. With neither, the receive time is used.
- A time more than a minute in the future is replaced with the receive time.

`created_at` is always the server's insert time.

## Reads

- `/api/events` pages with a keyset cursor on `(timestamp, id)` descending, so pages stay stable while new events arrive. A matching `(-timestamp, -id)` index serves it.
- `/api/insights` returns one point per minute in UTC, zero-filled, so the series always has `lookback_minutes` points.
- `/api/stats` summarizes the last 24 hours.

Every read is bounded by a `MAX_*` setting.

## Retention

Celery beat runs `purge_expired_events_task` hourly. It deletes events older than `EVENT_RETENTION_DAYS` in chunks of `EVENT_RETENTION_DELETE_BATCH_SIZE`, each in its own transaction, so a large backlog doesn't hold one long lock. `EVENT_RETENTION_DAYS=0` turns it off.

## Code layout

The backend separates HTTP from business logic:

| Layer | Path | Does |
|---|---|---|
| API | `events/api/` | Parses and validates requests (schemas), maps errors to status codes. |
| Services | `events/services/` | Writes and side effects. Plain dataclasses in and out, and domain exceptions; no HTTP types. |
| Selectors | `events/selectors/` | Read queries. |
| Tasks | `events/tasks/` | Celery tasks; the only place events are inserted. |

`backend/AGENTS.md` has the detailed rules, and `frontend/AGENTS.md` covers the dashboard.
