# backend/AGENTS.md

Django 5 + Django Ninja API, Celery worker, Postgres. Read the root [`AGENTS.md`](../AGENTS.md) first.

## Layout

```
backend/
├── telemetry_taco/          # Django *project*: settings, urls, NinjaAPI instance
│   ├── settings/            # base.py, development.py (default), test.py, production.py
│   ├── api.py               # NinjaAPI(); mounts core.api.router at /api/
│   └── urls.py
└── core/                    # the one Django app
    ├── api/
    │   ├── events.py        # Ninja router: HTTP only (parse, validate, map errors, status codes)
    │   └── schemas.py       # Pydantic/Ninja request + response schemas
    ├── services/            # business logic and side effects (ingestion, health)
    ├── selectors/           # read queries: return model instances or plain data
    ├── tasks/               # Celery tasks; persistence happens here
    ├── models.py            # Event
    ├── management/commands/ # check_db, seed_events, purge_expired_events, export_openapi_schema
    ├── celery.py            # Celery app (autodiscovers tasks)
    └── tests/               # pytest: test_api.py (HTTP), test_tasks.py (worker), test_commands.py
```

## Where code goes

| You are adding… | Put it in | Notes |
|---|---|---|
| A new endpoint | `core/api/events.py` (or a new router module wired up in `core/api/__init__.py`) | Keep handlers thin. Call a service or selector. |
| Request or response shape | `core/api/schemas.py` | Every input and output is a schema, never a raw `dict` or `request.body`. |
| A read query | `core/selectors/` | Keyword-only args, bounded by a `settings.MAX_*` limit. |
| A write or side effect | `core/services/` | Returns plain data. |
| Background work | `core/tasks/`, re-exported from `core/tasks/__init__.py` | Must be idempotent and safe to retry. |
| A config knob | `telemetry_taco/settings/base.py` via `env(...)` | Also add it to `.env.example`. |

## Ingestion path (don't break it)

1. `POST /api/capture` or `/api/capture/batch` → `EventCaptureSchema` validates the payload.
2. `services.ingestion.enqueue_events` enforces `MAX_CAPTURE_BATCH_SIZE`, fills in `event_uuid` and `timestamp`, and calls `process_event_batch_task.delay(...)` with JSON-serializable dicts.
3. `tasks.events.process_event_batch_task` builds `Event` objects and calls `bulk_create(ignore_conflicts=True)`. Duplicate `uuid`s are dropped by the DB unique constraint.
4. Only `OperationalError` triggers a retry. Any other exception in the task loses the whole batch, and the API has already returned 200. **So validate everything in the schema (step 1), not in the task.** For example, the DB column limits (`max_length=255`) must also be enforced on the schema.

Task arguments must stay JSON-serializable (`CELERY_TASK_SERIALIZER = "json"`), so pass ISO strings and `str(uuid)`, not `datetime` or `UUID` objects.

## Queries

- Every list endpoint is bounded: clamp with `min(requested, settings.MAX_…)`.
- Pagination on `/api/events` is a keyset cursor on `(timestamp, id)` descending. Keep `order_by("-timestamp", "-id")` and the tie-break filter together.
- `Event.Meta.ordering` is set, so call `.order_by()` explicitly in aggregates.
- `properties` is a JSONB field. If you filter on it, plan a GIN index in a migration.

## Settings and environment

- `DJANGO_SETTINGS_MODULE` defaults to `telemetry_taco.settings`, which loads **development**.
- Tests use `telemetry_taco.settings.test` (configured in `pyproject.toml`): in-memory SQLite unless `TEST_DATABASE_URL` is set, LocMem cache, `CELERY_TASK_ALWAYS_EAGER=True`, effectively unlimited rate limits. By default tests need no Postgres or Redis.
- Production refuses to start with the default or a short `SECRET_KEY`.
- `base.py` reads `backend/.env` if present. Never commit `.env`.

## Testing

```bash
poetry run pytest                          # all
poetry run pytest core/tests/test_api.py   # one file
poetry run pytest -k idempotent            # by name
poetry run pytest --cov                    # with coverage, as CI runs it

# on Postgres, like CI
docker compose up -d db
TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/telemetry_taco poetry run pytest
```

- Use the `client` fixture for HTTP-level tests, and `@pytest.mark.django_db` for anything touching the DB.
- Use the pytest-django `settings` fixture to override limits per test (see `test_capture_batch_rejects_oversized_batch`).
- Call task bodies directly with `.run(...)` in task tests.
- Because Celery runs eagerly in tests, a capture request persists synchronously, so assert on `Event.objects` right after the POST.
- CI runs the suite on Postgres 16, but local runs default to SQLite, which doesn't enforce `varchar` lengths and handles JSON and timezone truncation differently. If your change touches any of those, run the Postgres command above before pushing.

## Migrations

- Run `poetry run python manage.py makemigrations core`, then read the generated file.
- Keep `db_table = "core_event"` stable.
- Don't edit migrations that are already on `main`. Add a new one.

## Checks before pushing

```bash
poetry run ruff check . && poetry run ruff format --check .
DJANGO_SETTINGS_MODULE=telemetry_taco.settings.test poetry run python manage.py check
poetry run pytest
poetry run bandit -r . -c bandit.yaml       # CI runs this too
poetry run python manage.py check_db        # optional: is the dev database reachable?
```

If you changed an endpoint or schema, regenerate frontend types from the repo root with `pnpm generate:api-types`.
