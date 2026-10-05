# Deployment

> **There is no authentication yet** ([#30](https://github.com/Agile-Flimflam/TelemetryTaco/issues/30)). Anyone who can reach the API can send events and read every event back. Until that lands, run TelemetryTaco on a private network or behind something that authenticates (a VPN, an SSO proxy, HTTP basic auth on the frontend's nginx).

To try it on one machine, `docker compose up` from the repo root is enough (see the README). That stack runs development servers; this page is about running the production images.

## Images

Pushing a `v*` tag publishes two images to GHCR (`.github/workflows/release.yml`). `make images` builds the same ones locally.

- **`ghcr.io/agile-flimflam/telemetrytaco-backend`**: the API, the worker and beat, chosen by command. It runs as a non-root user with only the main dependencies, uses `config.settings.production`, and has a healthcheck on `/api/health/live`.
- **`ghcr.io/agile-flimflam/telemetrytaco-frontend`**: nginx serving the dashboard on port 8080. It proxies `/api`, `/admin` and `/static` to `API_UPSTREAM` (default `http://backend:8000`), so the browser talks to one origin.

Both are tagged with the release version (`1.2.3`), `latest`, and `sha-<commit>`. Images are amd64 only for now.

## Processes

Run one backend image per process:

| Process | Command | How many |
|---|---|---|
| Migrations | `python manage.py migrate --noinput` | Once per deploy, before the rest start |
| API | `gunicorn config.wsgi` (the image's default) | One or more |
| Worker | `celery -A config worker` | One or more |
| Beat | `celery -A config beat --schedule /tmp/celerybeat-schedule` | **Exactly one**, or each scheduled task runs once per beat |

Beat needs `--schedule` somewhere writable because the app directory isn't.

You also need Postgres (16 is what CI tests) and Redis.

## Example with Docker Compose

A minimal production stack. Put the secrets in a `.env` file next to it, not in the file itself.

```yaml
x-backend: &backend
  image: ghcr.io/agile-flimflam/telemetrytaco-backend:latest
  environment:
    SECRET_KEY: ${SECRET_KEY}
    DATABASE_URL: postgresql://telemetry:${POSTGRES_PASSWORD}@db:5432/telemetry
    REDIS_URL: redis://redis:6379/0
    CACHE_URL: redis://redis:6379/1
    ALLOWED_HOSTS: telemetry.example.com
    TRUSTED_PROXY_COUNT: "1"
  restart: unless-stopped
  # Everything waits for the migrations to finish.
  depends_on:
    migrate:
      condition: service_completed_successfully
    redis:
      condition: service_started

services:
  db:
    image: postgres:16
    environment:
      POSTGRES_USER: telemetry
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD}
      POSTGRES_DB: telemetry
    volumes: [postgres_data:/var/lib/postgresql/data]
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U telemetry"]
      interval: 5s
      retries: 10
    restart: unless-stopped

  redis:
    image: redis:7
    restart: unless-stopped

  migrate:
    <<: *backend
    command: python manage.py migrate --noinput
    restart: "no"
    depends_on:
      db:
        condition: service_healthy

  backend:
    <<: *backend
  worker:
    <<: *backend
    command: celery -A config worker
  beat:
    <<: *backend
    command: celery -A config beat --schedule /tmp/celerybeat-schedule

  frontend:
    image: ghcr.io/agile-flimflam/telemetrytaco-frontend:latest
    ports: ["8080:8080"]
    depends_on: [backend]
    restart: unless-stopped

volumes:
  postgres_data:
```

Put TLS in front of port 8080 with whatever terminates it for you (Caddy, Traefik, a cloud load balancer). If that adds a second proxy hop, set `TRUSTED_PROXY_COUNT` to `2`.

## Configuration

The backend reads its settings from environment variables. `backend/.env.example` lists them with development values.

| Variable | Default | Notes |
|---|---|---|
| `SECRET_KEY` | none in production | At least 50 characters. Production settings refuse to start without one. Generate with `python -c 'import secrets; print(secrets.token_urlsafe(50))'`. |
| `ALLOWED_HOSTS` | `localhost,127.0.0.1,0.0.0.0` | Comma-separated. Must include the hostname people use. |
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/telemetry_taco` | |
| `REDIS_URL` | `redis://localhost:6379/0` | Celery broker. |
| `CACHE_URL` | `redis://localhost:6379/1` | Django cache, which holds the rate-limit counters. |
| `CORS_ALLOWED_ORIGINS` | empty | Only needed when a browser calls the API from another origin. The frontend image serves both from one. |
| `TRUSTED_PROXY_COUNT` | 0 | How many reverse proxies sit in front of the backend. Rate limits then read the client IP from `X-Forwarded-For`. Use 1 behind the frontend image. Leave 0 if clients can reach the backend directly, since they could forge the header. |
| `RATE_LIMIT_CAPTURE_EVENT` | `1000/h` | Per client IP, for both capture endpoints. |
| `RATE_LIMIT_LIST_EVENTS` | `10000/h` | `/api/events`. |
| `RATE_LIMIT_GET_INSIGHTS` | `1000/h` | `/api/insights` and `/api/stats`. |
| `MAX_CAPTURE_BATCH_SIZE` | 500 | Events per batch request. |
| `MAX_EVENT_PROPERTIES_BYTES` | 32768 | Serialized size of one event's `properties`. |
| `MAX_EVENTS_LIMIT` | 200 | Largest `limit` on `/api/events`. |
| `MAX_INSIGHTS_LOOKBACK_MINUTES` | 1440 | Largest `lookback_minutes` on `/api/insights`. |
| `EVENT_RETENTION_DAYS` | 30 | Events older than this are purged hourly. 0 keeps everything. |
| `EVENT_RETENTION_DELETE_BATCH_SIZE` | 10000 | Rows per delete transaction during a purge. |
| `LOG_FORMAT` | `json` in production | `json` (one object per line) or `text`. |
| `LOG_LEVEL` | `INFO` | |
| `TIME_ZONE` | `UTC` | Django's time zone. The API returns UTC either way. |
| `PORT` | 8000 | Gunicorn's port. |
| `WEB_CONCURRENCY` | 2 per CPU | Gunicorn workers. |
| `GUNICORN_TIMEOUT` | 30 | Seconds before gunicorn restarts a stuck worker. |

The frontend image reads `API_UPSTREAM` and `PORT` (default 8080) at startup. `VITE_API_URL` is a build argument, only for serving the dashboard from a different origin than the API.

## Upgrading

Pull the new images, run the migrate command, then restart the other processes. Migrations are written to run before the new code starts.

A database created before the `core` to `events` rename (October 2026) needs `python manage.py migrate --fake-initial` once.
