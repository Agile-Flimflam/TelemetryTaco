# Contributing

Thanks for helping. This page covers setup, the checks a pull request has to pass, and the conventions reviewers look for. The `AGENTS.md` files (root, `backend/`, `frontend/`, `sdk/`) go deeper on each package, and they apply to people as much as to coding agents.

## Setup

You need:

- Python 3.11, 3.12 or 3.13, and [Poetry](https://python-poetry.org/) 2.x (CI pins 2.2.1)
- Node.js 22.22+ or 24, and [pnpm](https://pnpm.io/) 10
- Docker, for Postgres and Redis
- `make`

```bash
make setup   # backend and frontend dependencies, plus the pre-commit hooks
make dev     # Postgres and Redis in Docker, then the API, worker, beat and frontend
```

`make dev` runs the processes in `Procfile.dev` with honcho, all in one terminal. Ctrl-C stops them. The dashboard is on http://localhost:5173 and the API on http://localhost:8000. `make seed` adds demo events, and `make help` lists every target.

The settings defaults match `make dev`. To change one, copy `backend/.env.example` to `backend/.env`.

### Running the backend by hand

`make dev` is the same as these, from `backend/`, in four terminals:

```bash
docker compose up -d db redis                     # from the repo root
poetry run python manage.py migrate --fake-initial
poetry run python manage.py runserver
poetry run celery -A config worker --loglevel=info
poetry run celery -A config beat --loglevel=info
```

`--fake-initial` matters only for a database created before the `core` to `events` app rename, which already has the `core_event` table; on any other database it migrates normally.

### Useful management commands

```bash
poetry run python manage.py check_db                     # is the database reachable?
poetry run python manage.py seed_events --count 2000     # --clean wipes first, --if-empty skips a seeded DB
poetry run python manage.py purge_expired_events         # run the retention purge now
docker compose exec redis redis-cli -n 1 FLUSHDB         # reset rate-limit counters
```

## Checks

```bash
make validate            # everything below that needs no Docker
make validate-backend    # Ruff, Ruff format, Bandit, Django check, pytest
make validate-frontend   # regenerate API types, ESLint, Prettier, tsc, Vitest, build
make test-sdk            # SDK tests
make fmt                 # fix lint and formatting
```

The pre-commit hooks run Ruff, Prettier and ESLint on the files you commit.

CI also runs the backend tests on Postgres 16 under Python 3.11, 3.12 and 3.13, tests the SDK from a clean install, and builds the Docker images. Local tests use in-memory SQLite, which doesn't enforce `varchar` lengths and treats JSON and time zones differently. If your change touches queries, JSON fields, string lengths or time zones, run the suite on Postgres too:

```bash
docker compose up -d db
cd backend && TEST_DATABASE_URL=postgresql://postgres:postgres@localhost:5432/telemetry_taco poetry run pytest
```

## Conventions

- **The OpenAPI schema is the contract.** After changing a backend endpoint or schema, run `make types` and commit both `frontend/openapi.json` and `frontend/src/shared/api/generated.ts`. CI fails if they're stale. Never edit either by hand.
- **Keep the API backward compatible.** Add optional fields; don't rename or remove existing ones. Flag a breaking change in the PR description.
- **Ingestion never writes to the database in the request.** Capture endpoints validate, normalize and enqueue. [docs/architecture.md](docs/architecture.md) explains why.
- **Lockfiles are the source of truth.** Use `poetry add` and `pnpm add`.
- **No secrets in the repo.** Configuration comes from environment variables. Document new backend ones in `backend/.env.example` and [docs/deployment.md](docs/deployment.md#configuration).
- **Model changes** need `poetry run python manage.py makemigrations events`. Read the migration before committing.
- **Style:**
  - Python: type hints everywhere, Ruff with line length 100.
  - TypeScript: strict mode, no `any`, Prettier.
  - Name things after the domain (`event`, `insight`, `distinct_id`).
  - Comments explain why, not what.
- **Commits:** imperative mood and a short subject (`Add event name filter to /api/events`), with a body saying why when it isn't obvious.

## Pull requests

Keep each PR to one change. Unrelated cleanup goes in its own PR. The template asks for:

- what a user sees before and after the change, then how it works
- `make validate` passing, or the `validate-*` target for each package you touched
- a test for new behavior, and a test that fails without the fix for a bug
- for API changes, regenerated types and an updated [docs/api.md](docs/api.md)
- a `CHANGELOG.md` entry under **Unreleased** for anything a user would notice

## Reporting bugs and security issues

Open an issue with the bug template. For anything security-related, follow [SECURITY.md](SECURITY.md) instead of opening a public issue.
