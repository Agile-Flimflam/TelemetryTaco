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

See [docs/architecture.md](docs/architecture.md) for how ingestion, idempotency and event times work.

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

With Docker, one command runs the whole stack (Postgres, Redis, the API, the Celery worker and beat, and the dashboard) and seeds demo events on first boot:

```bash
docker compose up
```

Open http://localhost:5173. The API is on http://localhost:8000. `docker compose down` stops it and keeps your data, and `docker compose down -v` deletes it.

### Local development

Prerequisites:

- Python 3.11, 3.12, or 3.13
- Poetry 2.x
- Node.js 22.22+ or 24 and `pnpm`
- Docker, for Postgres and Redis
- `make`

```bash
make setup   # install dependencies and the pre-commit hooks
make dev     # Postgres and Redis in Docker, then the API, worker, beat and frontend
make seed    # optional: add demo events
```

The settings defaults match `make dev`. To change one, copy `backend/.env.example` to `backend/.env` and edit it.

`make dev` runs the processes in `Procfile.dev` with [honcho](https://honcho.readthedocs.io/), in one terminal with one log stream. Ctrl-C stops all of them. `make down` stops Postgres and Redis.

### Useful commands

`make help` lists every target. The common ones:

```bash
make types       # export the backend OpenAPI schema and regenerate frontend types
make lint        # Ruff, Bandit, ESLint, Prettier and tsc
make fmt         # fix lint issues and format everything
make test        # backend, frontend and SDK tests
make validate    # what CI runs that needs no Docker: types, lint, Django check, tests, build
make seed ARGS="--clean --count 5000"   # wipe and reseed demo events
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

The SDK batches events in a background thread and flushes when the context manager exits. See [docs/sdk.md](docs/sdk.md) for installing it and its options.

## Documentation

- [Architecture](docs/architecture.md): the ingestion path, idempotency, event times and retention
- [API](docs/api.md): every endpoint, its errors and its limits
- [Python SDK](docs/sdk.md): install, options and delivery guarantees
- [Deployment](docs/deployment.md): the production images, an example stack and every setting
- [Contributing](CONTRIBUTING.md), [Security](SECURITY.md) and the [Changelog](CHANGELOG.md)

## Status

TelemetryTaco is intentionally not solving multi-tenancy, auth, cohorts, funnels, feature flags, or ClickHouse analytics yet. The current code is optimized for a maintainable ingestion-and-dashboard MVP with clean seams for future expansion.

## License

TelemetryTaco is released under the [MIT License](LICENSE).
