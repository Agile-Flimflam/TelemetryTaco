# TelemetryTaco

TelemetryTaco is a lightweight self-hosted telemetry MVP built around three concrete workflows:

- capture single events or batches
- inspect recent events in a live dashboard
- query minute-level insight aggregates over a recent lookback window

![TelemetryTaco dashboard](docs/screenshots/dashboard.png)

The codebase now targets a strong single-project MVP rather than a broad PostHog clone. The refactor in this repo keeps the current API contract intact while adding real batching, idempotency, generated frontend types, tests, and a cleaner developer workflow.

## Current Architecture

```text
Python SDK / API clients
        |
        v
  Django + Django Ninja
        |
        v
 Celery batch task queue
        |
        v
 PostgreSQL event store
        |
        v
 React dashboard (React Query + generated OpenAPI types)
```

### Runtime responsibilities

- `backend/`: API surface, ingestion service, selectors, Celery tasks, retention commands
- `frontend/`: dashboard UI, React Query polling, OpenAPI-generated TypeScript types
- `sdk/`: queue-backed Python client that batches to `/api/capture/batch`

## What Exists Today

- `POST /api/capture`: additive single-event capture endpoint
- `POST /api/capture/batch`: batch capture endpoint used by the SDK
- `GET /api/events`: bounded recent-event feed with optional `before` cursor
- `GET /api/insights`: bounded minute-level aggregate series
- `GET /api/stats`: event count, unique `distinct_id`s and last received event for the dashboard header
- `GET /api/health/live` and `GET /api/health/ready`
- event idempotency via caller-supplied `event_uuid`
- OpenAPI export and generated frontend types
- backend pytest coverage, frontend Vitest coverage, and SDK tests

## Quick Start

### Prerequisites

- Python 3.11, 3.12, or 3.13
- Poetry
- Node.js 18+ and `pnpm`
- Docker and Docker Compose

### Local development

1. Copy backend environment defaults:

```bash
cp backend/.env.example backend/.env
```

2. Start the database and Redis:

```bash
docker-compose up -d db redis
```

3. Start the application stack:

```bash
./start.sh
```

That script will install backend dependencies, run migrations, start Django and Celery in the background, and run the frontend in the foreground.

### Useful commands

```bash
pnpm generate:api-types   # export backend OpenAPI and regenerate frontend types
pnpm validate:backend     # Ruff + format check + Django check + backend pytest
pnpm validate:frontend    # OpenAPI type generation + lint + type-check + Vitest
pnpm validate:all         # backend + frontend + SDK validation
pnpm test                 # backend + frontend + SDK tests
pnpm seed                 # seed realistic sample events
pnpm seed:clean           # wipe and reseed events
```

## Backend Notes

The backend defaults to development settings via `telemetry_taco.settings`.

Available settings modules:

- `telemetry_taco.settings.development`
- `telemetry_taco.settings.test`
- `telemetry_taco.settings.production`

Important environment variables:

- `DATABASE_URL`
- `REDIS_URL`
- `CACHE_URL`
- `MAX_CAPTURE_BATCH_SIZE`
- `MAX_EVENT_PROPERTIES_BYTES` (default 32768)
- `MAX_EVENTS_LIMIT`
- `MAX_INSIGHTS_LOOKBACK_MINUTES`
- `EVENT_RETENTION_DAYS`
- `RATE_LIMIT_CAPTURE_EVENT`, `RATE_LIMIT_LIST_EVENTS`, `RATE_LIMIT_GET_INSIGHTS` (per client IP, for example `1000/h`)
- `TRUSTED_PROXY_COUNT`

Rate limits are per client IP. Behind a reverse proxy or load balancer, every request arrives from the proxy's address, so all clients would share one limit. Set `TRUSTED_PROXY_COUNT` to the number of proxies in front of the backend (usually 1) and the client IP is read from `X-Forwarded-For` instead. Leave it at 0 when clients can reach the backend directly, since they could forge that header.

Retention cleanup is exposed as a management command:

```bash
cd backend
poetry run python manage.py purge_expired_events
```

OpenAPI export is also explicit:

```bash
cd backend
DJANGO_SETTINGS_MODULE=telemetry_taco.settings.test poetry run python manage.py export_openapi_schema ../frontend/openapi.json
```

## Frontend Notes

The dashboard is a Vite React app that uses:

- React Query for polling, deduping, and error handling
- lazy loading for the chart surface
- generated API types from `frontend/openapi.json`

If the backend contract changes, regenerate types before committing:

```bash
pnpm generate:api-types
```

## SDK Example

```python
from telemetry_taco import TelemetryTaco

with TelemetryTaco(base_url="http://localhost:8000") as client:
    client.capture(
        distinct_id="user-123",
        event_name="feature_used",
        properties={"feature_name": "insights-refresh"},
    )
```

The SDK batches events in a background worker, attaches `event_uuid` and `sent_at`, and flushes automatically when the context manager exits.

## API Summary

### `POST /api/capture`

```json
{
  "distinct_id": "user-123",
  "event_name": "page_view",
  "properties": {
    "path": "/"
  },
  "event_uuid": "optional-uuid",
  "sent_at": "YYYY-MM-DDTHH:MM:SSZ"
}
```

`distinct_id` and `event_name` must be 1 to 255 characters. `properties` may be at most `MAX_EVENT_PROPERTIES_BYTES` once serialized as JSON. No string may contain a NUL character. Anything else is rejected with HTTP 422, and in a batch one invalid event rejects the whole request, so nothing is accepted and then lost later.

Response:

```json
{
  "status": "ok"
}
```

### `POST /api/capture/batch`

```json
{
  "events": [
    {
      "distinct_id": "user-123",
      "event_name": "page_view"
    }
  ]
}
```

### `GET /api/events?limit=100&before=YYYY-MM-DDTHH:MM:SSZ,EVENT_ID`

Returns recent events ordered by `timestamp desc, id desc`.
For stable pagination, set `before` to the last event's `timestamp,id` pair.
Plain ISO 8601 timestamps are still accepted for backward compatibility.

### `GET /api/insights?lookback_minutes=60`

Returns minute buckets shaped like:

```json
[
  { "time": "18:04", "count": 4 }
]
```

### `GET /api/stats`

Returns a summary of the last 24 hours plus when the most recent event arrived:

```json
{
  "events_last_24h": 2999,
  "unique_distinct_ids_last_24h": 75,
  "last_event_received_at": "2026-10-04T07:42:00.310Z"
}
```

## Developer Workflow

- Use `pnpm` at the repo root for day-to-day commands.
- Treat `backend/poetry.lock` and `pnpm-lock.yaml` as the dependency source of truth.
- Do not reintroduce `npm` lockfiles or a standalone backend `requirements.txt`.
- Keep frontend API types generated from the backend schema, not hand-maintained.

## Status

TelemetryTaco is intentionally not solving multi-tenancy, auth, cohorts, funnels, feature flags, or ClickHouse analytics yet. The current code is optimized for a maintainable ingestion-and-dashboard MVP with clean seams for future expansion.

## License

TelemetryTaco is released under the [MIT License](LICENSE).
