# Backend Setup

## Purpose

The backend handles event ingestion, persistence, recent-event queries, health checks, and retention cleanup. It is a Django 5 app with Django Ninja, Celery, PostgreSQL, and Redis.

## Environment

Copy the example file first:

```bash
cp .env.example .env
```

Core variables:

```env
DEBUG=True
SECRET_KEY=dev-only-secret-key-not-for-production-use-please-change-me-12345
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/telemetry_taco
REDIS_URL=redis://localhost:6379/0
CACHE_URL=redis://localhost:6379/1
MAX_CAPTURE_BATCH_SIZE=500
MAX_EVENTS_LIMIT=200
MAX_INSIGHTS_LOOKBACK_MINUTES=1440
EVENT_RETENTION_DAYS=30
```

Settings modules:

- default local development: `config.settings`
- explicit development: `config.settings.development`
- tests: `config.settings.test`
- production: `config.settings.production`

## Install

Use a supported Python version first:

```bash
poetry env use python3.13
POETRY_CACHE_DIR=/tmp/pypoetry-cache poetry install
```

## Run

Start dependencies from the repo root:

```bash
docker-compose up -d db redis
```

Run migrations:

```bash
poetry run python manage.py migrate
```

A database created before the Django app was renamed from `core` to `events` already has the `core_event` table, so run `poetry run python manage.py migrate --fake-initial` once instead.

Start the API server:

```bash
poetry run python manage.py runserver
```

Start the worker in another shell:

```bash
poetry run celery -A config worker -B --loglevel=info
```

## Validation

```bash
poetry run ruff check .
poetry run ruff format --check .
DJANGO_SETTINGS_MODULE=config.settings.test poetry run python manage.py check
POETRY_CACHE_DIR=/tmp/pypoetry-cache poetry run pytest
```

## Commands

Check that the database is reachable:

```bash
poetry run python manage.py check_db
```

Seed sample data:

```bash
poetry run python manage.py seed_events --count 2000
```

Purge expired events:

```bash
poetry run python manage.py purge_expired_events
```

Export the OpenAPI schema:

```bash
DJANGO_SETTINGS_MODULE=config.settings.test poetry run python manage.py export_openapi_schema ../frontend/openapi.json
```

## Notes

- The current backend is optimized for a strong single-project MVP.
- `event_uuid` drives idempotency.
- `/api/capture` and `/api/capture/batch` both enqueue through the same ingestion service.
- The dashboard contract should be treated as OpenAPI-first; regenerate frontend types whenever the API changes.
