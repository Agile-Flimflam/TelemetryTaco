# Changelog

Notable changes to TelemetryTaco. The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses [Semantic Versioning](https://semver.org/).

## [Unreleased]

### Added

- `GET /api/stats` and a dashboard header with events and unique users over the last 24 hours.
- `timestamp` on captured events, so clients can record when an event happened. With `sent_at`, the server corrects for a wrong client clock.
- `bucket` on insight points: the minute's start as an ISO 8601 UTC time.
- Hourly retention purge through Celery beat, deleting in chunks (`EVENT_RETENTION_DAYS`, `EVENT_RETENTION_DELETE_BATCH_SIZE`).
- `TRUSTED_PROXY_COUNT`, so rate limits work per client behind a reverse proxy.
- `MAX_EVENT_PROPERTIES_BYTES` to cap the size of an event's properties.
- Production Docker images for the backend (gunicorn, non-root) and the dashboard (nginx), published to GHCR on release tags.
- `docker compose up` runs the whole stack and seeds demo data on first boot, and `make dev` runs it locally in one terminal.
- `LOG_FORMAT=json` for one-JSON-object-per-line logs; task logs now include their counts.
- Per-card error boundaries in the dashboard.
- Docs: architecture, API, SDK and deployment guides, plus contributing and security policies.

### Changed

- Insights are zero-filled, one point per minute in UTC, so the chart no longer draws lines across quiet periods.
- `accepted` and the task logs count each `event_uuid` once.
- The SDK sends queued events when the interpreter exits, and the `block` queue policy no longer raises `queue.Full`.
- The backend packages are now `config` (project) and `events` (app). Run Celery with `celery -A config`. Existing databases need `manage.py migrate --fake-initial` once.
- The dashboard is built with React 19 and Vite 8.
- `make` is the one entry point for development (`make help`).
- The dashboard loads the chart library only when the chart renders.

### Removed

- `start.sh`, `stop.sh`, `restart-backend.sh`, `seed.sh` and `clear-rate-limit.sh`, and the root `pnpm` scripts other than four frontend ones.
- `Event.updated_at`. Events never change after they're stored.

### Fixed

- Capture rejects values the database can't store (over-long strings, NUL characters) with a 422, instead of accepting them and losing the batch in the worker.
- The insights chart no longer exceeds the production rate limit while polling.
- Docker Compose sets `CACHE_URL`, so rate limits and readiness checks use Redis.

## [0.1.0] - 2026-03-13

The first version: event capture (single and batch) with idempotency by `event_uuid`, a Celery worker writing to Postgres, a React dashboard with a live event feed and per-minute counts, and a batching Python SDK.

[Unreleased]: https://github.com/Agile-Flimflam/TelemetryTaco/compare/a49acf6...HEAD
[0.1.0]: https://github.com/Agile-Flimflam/TelemetryTaco/tree/a49acf6
