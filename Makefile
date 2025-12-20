.PHONY: help start stop dev services migrate test clean

help: ## Show this help message
	@echo "TelemetryTaco Development Commands"
	@echo ""
	@echo "Usage: make [target]"
	@echo ""
	@echo "Targets:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  %-15s %s\n", $$1, $$2}'

services: ## Start Docker services (PostgreSQL & Redis)
	@echo "🌮 Starting Docker services..."
	docker-compose up -d db redis
	@echo "⏳ Waiting for PostgreSQL..."
	@timeout=30; \
	counter=0; \
	until docker-compose exec -T db pg_isready -U postgres > /dev/null 2>&1; do \
		sleep 1; \
		counter=$$((counter + 1)); \
		if [ $$counter -ge $$timeout ]; then \
			echo "❌ PostgreSQL failed to start"; \
			exit 1; \
		fi; \
	done
	@echo "✅ Services ready"

install: ## Install all dependencies
	@echo "📦 Installing dependencies..."
	cd backend && poetry install
	cd frontend && pnpm install
	@echo "✅ Dependencies installed"

migrate: install ## Run database migrations (installs dependencies first)
	@echo "🔄 Running migrations..."
	cd backend && poetry run python manage.py migrate

dev: services install migrate ## Start all development servers (backend, worker, frontend)
	@echo "🚀 Starting development servers..."
	@echo "📝 Backend: http://localhost:8000"
	@echo "📝 Frontend: http://localhost:5173"
	@echo ""
	@echo "Starting in background..."
	@cd backend && poetry run python manage.py runserver > ../.backend.log 2>&1 & echo $$! > ../.backend.pid
	@cd backend && poetry run celery -A core worker --loglevel=info > ../.celery.log 2>&1 & echo $$! > ../.celery.pid
	@echo "✅ Backend and Celery started in background"
	@echo "▶️  Starting frontend (foreground)..."
	@cd frontend && pnpm dev

start: dev ## Alias for 'dev'

stop: ## Stop all development servers
	@echo "🛑 Stopping services..."
	@if [ -f .backend.pid ]; then \
		kill $$(cat .backend.pid) 2>/dev/null || true; \
		rm .backend.pid; \
		echo "✅ Stopped backend"; \
	fi
	@if [ -f .celery.pid ]; then \
		kill $$(cat .celery.pid) 2>/dev/null || true; \
		rm .celery.pid; \
		echo "✅ Stopped Celery"; \
	fi
	@echo "✅ All services stopped"

clean: stop ## Stop services and clean up logs
	@rm -f .backend.log .celery.log
	@echo "✅ Cleaned up"

test: ## Run tests
	@echo "🧪 Running tests..."
	cd backend && poetry run python manage.py test
	cd frontend && pnpm test || true

seed: ## Seed database with historical event data
	@echo "📊 Seeding database..."
	cd backend && poetry run python manage.py seed_events

seed-clean: ## Clean and seed database (deletes existing events first)
	@echo "📊 Cleaning and seeding database..."
	cd backend && poetry run python manage.py seed_events --clean
