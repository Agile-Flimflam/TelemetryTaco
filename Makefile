.DEFAULT_GOAL := help

BACKEND := cd backend && poetry run
FRONTEND := pnpm --dir frontend
COMPOSE := docker compose

.PHONY: help setup services down migrate dev docker seed types \
	lint lint-backend lint-frontend fmt check \
	test test-backend test-frontend test-sdk build \
	validate validate-backend validate-frontend

help: ## Show this help
	@awk 'BEGIN {FS = ":.*## "} /^## / {printf "\n%s\n", substr($$0, 4)} /^[a-zA-Z_-]+:.*## / {printf "  %-18s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

## Running

setup: ## Install dependencies and the pre-commit hooks
	cd backend && poetry install
	pnpm install
	poetry --project backend run pre-commit install

services: ## Start Postgres and Redis in Docker
	$(COMPOSE) up -d --wait db redis

down: ## Stop every Docker service (data volumes are kept)
	$(COMPOSE) down

# --fake-initial adopts the core_event table in databases from before the core -> events rename.
migrate: ## Apply database migrations
	$(BACKEND) python manage.py migrate --fake-initial

dev: services migrate ## Run the API, worker, beat and frontend locally; Ctrl-C stops them all
	poetry --project backend run honcho --procfile Procfile.dev start

docker: ## Run the whole stack in Docker, seeded with demo data
	$(COMPOSE) up --build

seed: ## Add demo events; pass options with ARGS="--clean --count 5000"
	$(BACKEND) python manage.py seed_events $(ARGS)

## Checks

types: ## Export the OpenAPI schema and regenerate the frontend API types
	cd backend && DJANGO_SETTINGS_MODULE=config.settings.test poetry run python manage.py export_openapi_schema ../frontend/openapi.json
	$(FRONTEND) generate:api-types

lint: lint-backend lint-frontend ## Lint and type-check everything

lint-backend: ## Ruff, Ruff format check and Bandit
	$(BACKEND) ruff check .
	$(BACKEND) ruff format --check .
	$(BACKEND) bandit -q -r . -c bandit.yaml

lint-frontend: ## ESLint, Prettier check and tsc
	$(FRONTEND) lint
	$(FRONTEND) format:check
	$(FRONTEND) type-check

fmt: ## Fix lint issues and format everything
	$(BACKEND) ruff check --fix .
	$(BACKEND) ruff format .
	$(FRONTEND) lint --fix
	$(FRONTEND) format

check: ## Django system check
	cd backend && DJANGO_SETTINGS_MODULE=config.settings.test poetry run python manage.py check

test: test-backend test-frontend test-sdk ## Run every test suite

test-backend: ## Backend tests (SQLite unless TEST_DATABASE_URL is set)
	$(BACKEND) pytest

test-frontend: ## Frontend tests
	$(FRONTEND) test

# The SDK has no dependencies of its own, so it borrows pytest from the backend's venv.
test-sdk: ## SDK tests
	cd sdk && "$$(cd ../backend && poetry run python -c 'import sys; print(sys.executable)')" -m pytest tests

build: ## Build the frontend
	$(FRONTEND) build

validate: validate-backend validate-frontend test-sdk ## Run what CI runs that needs no Docker

validate-backend: lint-backend check test-backend ## Validate the backend

validate-frontend: types lint-frontend test-frontend build ## Validate the frontend
