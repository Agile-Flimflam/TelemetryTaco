# AGENTS.md

Guidance for AI coding agents (and humans) working in this repository. Scoped guides with more detail live next to the code:

- [`backend/AGENTS.md`](backend/AGENTS.md): Django, Ninja, Celery
- [`frontend/AGENTS.md`](frontend/AGENTS.md): React dashboard
- [`sdk/AGENTS.md`](sdk/AGENTS.md): Python client library

When guides disagree, the one closest to the file you are editing wins.

## What this project is

TelemetryTaco is a small self-hosted event analytics stack. Clients send events to an HTTP API. A Celery worker persists them to Postgres, and a React dashboard shows a live event feed and per-minute counts.

```
sdk/ (Python client) ──POST /api/capture/batch──► backend/ (Django + Ninja)
                                                    │ enqueue
                                                    ▼
                                         Celery worker ──bulk_create──► Postgres
                                                                            │
frontend/ (React dashboard) ◄──GET /api/events, /api/insights───────────────┘
```

Three packages, three toolchains:

| Path | Language | Package manager | Tests |
|---|---|---|---|
| `backend/` | Python 3.11–3.13, Django 5, Django Ninja, Celery | Poetry (`backend/poetry.lock`) | pytest + pytest-django |
| `frontend/` | TypeScript, React 18, Vite, Tailwind, shadcn/ui, React Query | pnpm workspace (`pnpm-lock.yaml` at root) | Vitest + Testing Library |
| `sdk/` | Python 3.11+, standard library only | setuptools (`sdk/pyproject.toml`) | pytest |

## Commands

Run these from the repo root. Each one is what CI runs, so a clean local run means CI should pass.

```bash
# one-time setup
cd backend && poetry install && cd ..
pnpm install

# backend: lint, format check, Django system check, tests
pnpm validate:backend

# frontend: regenerate API types, lint, type-check, tests, build
pnpm validate:frontend

# SDK tests (borrows the backend's Poetry venv for pytest)
pnpm test:sdk

# everything
pnpm validate:all
```

Narrower loops while iterating:

```bash
cd backend && poetry run pytest core/tests/test_api.py -k cursor   # one backend test
cd backend && poetry run ruff check --fix . && poetry run ruff format .
cd frontend && pnpm vitest run src/features/events                 # one frontend folder
cd frontend && pnpm lint && pnpm type-check
```

Backend and frontend tests need **no** running services. The test settings use SQLite, an in-memory cache and eager Celery. Only the full app (`./start.sh` or `make dev`) needs Docker for Postgres and Redis.

## Rules that span packages

1. **The OpenAPI schema is the contract.** After changing any backend schema or endpoint, run `pnpm generate:api-types` and commit both `frontend/openapi.json` and `frontend/src/shared/api/generated.ts`. CI regenerates them and fails on any diff. Never hand-edit either file.
2. **Keep the API backward compatible.** The SDK and any deployed clients call `/api/capture` and `/api/capture/batch`. Add optional fields, don't rename or remove existing ones. If a breaking change is truly needed, flag it in the PR description.
3. **Idempotency comes from `event_uuid`.** Every event carries a UUID, and the DB unique constraint plus `bulk_create(ignore_conflicts=True)` drop duplicates. Don't add a second dedup mechanism, and don't remove the UUID from any path.
4. **Ingestion never writes to the DB in the request.** Capture endpoints validate, normalize and enqueue a Celery task, then return. Keep it that way.
5. **The lockfiles are the source of truth.** Use `poetry add` / `pnpm add`. Don't add `requirements.txt`, `package-lock.json` or `yarn.lock`.
6. **No secrets in the repo.** Configuration comes from environment variables (`django-environ` on the backend, `import.meta.env.VITE_*` on the frontend). Document new backend variables in `backend/.env.example`. Frontend `VITE_*` variables are read by Vite from `frontend/.env*` (not `backend/.env`), so document those in `frontend/AGENTS.md` and the README.

## Definition of done

Before you call a change finished:

- [ ] `pnpm validate:all` passes, or at least the `validate:*` target for each package you touched.
- [ ] New behavior has a test. Bug fixes have a test that fails without the fix.
- [ ] API changes: types regenerated and committed (rule 1), and the README's API section updated.
- [ ] Model changes: `poetry run python manage.py makemigrations` was run, and the migration was read before committing.
- [ ] New environment variables are documented: backend ones in `backend/.env.example`, frontend `VITE_*` ones in `frontend/AGENTS.md` and the README.
- [ ] The diff is limited to the task. Unrelated cleanup goes in its own PR.

## Things that will surprise you

These are known rough edges. Don't paper over them silently in an unrelated change, but feel free to fix one as its own focused PR.

- **Two packages are named `telemetry_taco`.** One is the Django project (`backend/telemetry_taco/`) and the other is the SDK (`sdk/telemetry_taco/`). Never install the SDK into the backend environment. The SDK tests only work because they run from inside `sdk/`.
- **There is no authentication.** Every endpoint is public. Don't build features that assume a user or project exists without adding that layer first.
- **Rate limits are per client IP.** That's `REMOTE_ADDR` unless `TRUSTED_PROXY_COUNT` is set, in which case it's read from `X-Forwarded-For` (`core/api/ratelimit.py`). They're configured with `RATE_LIMIT_*` settings, and the test settings set them effectively unlimited.
- **`sent_at` from the client is stored as the event's `timestamp`.** It doesn't mean "time sent".
- **Several overlapping ways to run things** exist: `start.sh`, `stop.sh`, `restart-backend.sh`, `seed.sh`, the `Makefile` and root `package.json` scripts. Prefer the `pnpm` scripts above, and don't add new shell scripts.
- `backend/test.sqlite3` is a committed artifact of the test settings. Don't commit changes to it.

## Style

- Match the surrounding code. Comments explain *why*, not *what*.
- Python: type hints on every function, modern syntax (`list[str]`, `X | None`), Ruff for lint and format (line length 100).
- TypeScript: `strict` mode, no `any` (ESLint enforces this), `@/` imports instead of deep relative paths.
- Name things after the domain (`event`, `insight`, `distinct_id`), not the framework.
- Commits: imperative mood, a short subject (`Add event name filter to /api/events`), and a body explaining why if it isn't obvious.
