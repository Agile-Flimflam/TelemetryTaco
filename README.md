# 🌮 TelemetryTaco

<div align="center">

![Python](https://img.shields.io/badge/python-3.11%20%7C%203.12-blue.svg)
![Django](https://img.shields.io/badge/django-5.0+-green.svg)
![React](https://img.shields.io/badge/react-18.2.0-61dafb.svg)
![TypeScript](https://img.shields.io/badge/typescript-5.3.3-3178c6.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Poetry](https://img.shields.io/badge/poetry-2.2+-orange.svg)

**Lightweight, high-performance telemetry tool designed to correlate Feature Usage with System Health in real-time**

[Features](#-features) • [Quick Start](#-quick-start) • [Architecture](#-architecture) • [Documentation](#-documentation)

</div>

---

## ✨ Features

- 🚀 **Sub-10ms Ingestion Latency** - Async architecture ensures API responses return immediately
- 📊 **Real-time Insights Dashboard** - Beautiful, developer-centric UI built with React + Shadcn UI
- 🔄 **Idempotent Event Processing** - UUID-based deduplication prevents duplicate events
- 📦 **Flexible Event Schema** - JSONB storage allows dynamic properties without migrations
- ⚡ **Horizontal Scalability** - Celery workers can scale independently from API servers
- 🎯 **Type-Safe SDK** - Python SDK with full type hints for seamless integration
- 🐳 **Docker-Ready** - One-command deployment with Docker Compose

---

## 🏗️ Architecture

```mermaid
graph LR
    SDK[SDK] -->|"HTTP POST"| APIServer["API Server"]
    APIServer -->|"Queue Task"| Redis[Redis]
    Redis -->|Consume| CeleryWorker["Celery Worker"]
    CeleryWorker -->|Write| PostgreSQL[PostgreSQL]
    PostgreSQL -->|Query| FrontendDashboard["Frontend Dashboard"]
```

### Component Overview

- **SDK** (`sdk/telemetry_taco.py`) - Non-blocking Python client that sends events in background threads
- **API Server** (Django + Django Ninja) - Fast, type-safe REST API with Pydantic validation
- **Redis** - Message broker for Celery task queue
- **Celery Worker** - Async event processor that writes to PostgreSQL
- **PostgreSQL** - Primary data store with JSONB for flexible event properties
- **Frontend Dashboard** (React + TypeScript) - Real-time visualization of telemetry data

---

## 🚀 Quick Start

> **New to the project?** Start here! For detailed setup instructions and troubleshooting, see the sections below.

### Fastest Way to Start (Recommended)

After initial setup, start everything with one command:

**First time setup** (make scripts executable):

```bash
chmod +x start.sh stop.sh
```

**Then start everything:**

```bash
# Option 1: Using the startup script (easiest)
./start.sh

# Option 2: Using pnpm
pnpm start

# Option 3: Using Make
make dev

# To stop all services:
./stop.sh  # or: pnpm stop  # or: make stop
```

The startup script will:

1. ✅ Start Docker services (PostgreSQL & Redis)
2. ✅ Wait for PostgreSQL to be ready
3. ✅ Create `.env` file if missing
4. ✅ Run database migrations
5. ✅ Start Django backend server (background)
6. ✅ Start Celery worker (background)
7. ✅ Start frontend dev server (foreground)

**Access the application:**

- Frontend: http://localhost:5173
- Backend API: http://localhost:8000
- API Docs: http://localhost:8000/api/docs

### Prerequisites

- Docker & Docker Compose
- Python 3.11 or 3.12 (for local development)
- Poetry (for Python dependency management)
- Node.js 18+ & pnpm (for frontend development)

### Manual Setup (Step-by-Step)

If you prefer to start services manually or the startup script doesn't work:

```bash
# Clone the repository
git clone https://github.com/yourusername/TelemetryTaco.git
cd TelemetryTaco

# 1. Start database and Redis services
docker-compose up -d db redis

# 2. Wait 5-10 seconds for PostgreSQL to initialize, then verify:
docker-compose ps db  # Should show "Up" and "healthy"

# 3. Set up backend (in backend/ directory)
cd backend
poetry env use python3.11  # Required if you have Python 3.14+
poetry install

# 4. Generate a secure SECRET_KEY and create .env file
# First, generate a secure SECRET_KEY:
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Copy the generated key, then create .env file (replace YOUR_SECRET_KEY with the generated key)
# Check your Docker container credentials first:
# docker-compose exec db env | grep POSTGRES
cat > .env << 'EOF'
DEBUG=True
SECRET_KEY=YOUR_SECRET_KEY
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/telemetry_taco
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
EOF
# Replace YOUR_SECRET_KEY with the generated key from above
# Update DATABASE_URL if your Docker container uses different credentials

# 5. Test database connection
poetry run python check_db.py

# 6. Run migrations
poetry run python manage.py migrate

# 7. Start backend server
poetry run python manage.py runserver
# Backend will be available at http://localhost:8000

# 8. In another terminal, start Celery worker
cd backend
poetry run celery -A core worker --loglevel=info

# 9. In another terminal, start frontend
cd frontend
pnpm install
pnpm dev
# Frontend will be available at http://localhost:5173

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

**Note**: For full Docker deployment (all services in containers), see `docker-compose.yml`. The above setup is recommended for local development.

### Development Commands Reference

After initial setup, use these commands for daily development:

```bash
# Start everything (recommended)
./start.sh          # or: pnpm start  # or: make dev

# Start individual services
pnpm dev:frontend   # Frontend only
pnpm dev:backend    # Backend only
pnpm dev:worker     # Celery worker only
pnpm services       # Docker services only

# Database operations
pnpm migrate        # Run migrations
make migrate        # Alternative

# Seed database with sample data
pnpm seed           # or: ./seed.sh
pnpm seed:clean     # or: ./seed.sh --clean (cleans existing data first)

# Code quality and validation
pnpm lint:backend   # Lint backend code (ruff check)
pnpm lint:frontend  # Lint frontend code (eslint)
pnpm format:backend # Format backend code (ruff format)
pnpm validate:backend   # Full backend validation (lint + format check + Django check)
pnpm validate:frontend # Full frontend validation (lint + type-check)
pnpm validate:all   # Validate both backend and frontend

# Stop services
./stop.sh           # or: pnpm stop  # or: make stop

# View all Make commands
make help
```

**Note**: On first run, make the scripts executable:

```bash
chmod +x start.sh stop.sh
```

### Local Development

#### Backend Setup

```bash
cd backend

# Configure Poetry to use Python 3.11 (required if you have Python 3.14+)
poetry env use python3.11
# Or specify full path: poetry env use /opt/homebrew/bin/python3.11

# Install dependencies with Poetry
poetry install

# Set up environment variables
# First, generate a secure SECRET_KEY:
python3 -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'

# Create .env file in backend/ directory (replace YOUR_SECRET_KEY with the generated key)
cat > .env << 'EOF'
DEBUG=True
SECRET_KEY=YOUR_SECRET_KEY
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/telemetry_taco
REDIS_URL=redis://localhost:6379/0
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
EOF
# Replace YOUR_SECRET_KEY with the generated key from above

# Note: If your Docker PostgreSQL uses different credentials, update DATABASE_URL accordingly.
# Important: The SECRET_KEY must be at least 50 characters and cannot use example/insecure values.
# Check your Docker container: docker-compose exec db env | grep POSTGRES

# Start database and Redis (from project root)
cd ..
docker-compose up -d db redis

# Wait 5-10 seconds for PostgreSQL to initialize, then verify:
docker-compose ps db

# Test database connection
cd backend
poetry run python check_db.py

# Run migrations
poetry run python manage.py migrate

# Start Django server
poetry run python manage.py runserver

# In another terminal, start Celery worker
cd backend
poetry run celery -A core worker --loglevel=info
```

**Troubleshooting**: If you encounter database connection issues, see [Backend Setup Guide](backend/SETUP.md) for detailed troubleshooting steps.

#### Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Start development server
# The Vite dev server is configured to proxy /api/* requests to http://localhost:8000
pnpm dev
```

The frontend will be available at `http://localhost:5173` and will automatically proxy API requests to the backend.

### Database Seeding

To populate the database with sample historical event data for testing and development:

```bash
# Seed database with historical events
pnpm seed           # or: ./seed.sh

# Clean existing events and seed fresh data
pnpm seed:clean     # or: ./seed.sh --clean
```

The seed command generates realistic event data with timestamps spanning the past 7 days, useful for testing the dashboard and insights features.

### Using the SDK

```python
# Option 1: Direct import (for development)
import sys
sys.path.insert(0, 'path/to/TelemetryTaco/sdk')
from telemetry_taco import TelemetryTaco

# Option 2: Install as package (recommended)
# pip install -e ./sdk
# from telemetry_taco import TelemetryTaco

# Initialize client
client = TelemetryTaco(base_url="http://localhost:8000")

# Capture an event (non-blocking)
client.capture(
    distinct_id="user_123",
    event_name="feature_used",
    properties={
        "feature_name": "dark_mode",
        "page": "settings",
        "system_health": {
            "cpu_usage": 45.2,
            "memory_usage": 62.1
        }
    }
)

# Use context manager to ensure events are sent before exit
with TelemetryTaco(base_url="http://localhost:8000") as client:
    client.capture(distinct_id="user_123", event_name="page_view")
    # Events are automatically flushed on exit
```

---

## 🤔 Why Async?

TelemetryTaco decouples **event ingestion** from **event processing** to achieve optimal performance and reliability.

### The Problem

Traditional synchronous architectures force API endpoints to wait for database writes, creating several issues:

- **High Latency**: Database writes (especially with indexes) can take 50-200ms, directly impacting API response times
- **Poor Scalability**: Database connections become a bottleneck under high load
- **Single Point of Failure**: If the database is slow or unavailable, the entire API becomes unresponsive
- **No Backpressure Handling**: Sudden traffic spikes can overwhelm the database

### The Solution

By using Redis as a message broker and Celery for async processing:

1. **API Returns Immediately** - Endpoints respond in <10ms, regardless of database load
2. **Independent Scaling** - API servers and Celery workers scale independently based on their specific bottlenecks
3. **Resilience** - If the database is temporarily unavailable, events queue in Redis and process when it recovers
4. **Rate Limiting** - Redis can handle millions of operations per second, providing natural backpressure
5. **Idempotency** - UUID-based deduplication in Celery tasks prevents duplicate processing

### Performance Characteristics

| Metric                  | Synchronous       | Async (TelemetryTaco) |
| ----------------------- | ----------------- | --------------------- |
| API Response Time       | 50-200ms          | <10ms                 |
| Throughput (events/sec) | ~1,000            | 10,000+               |
| Database Load           | High (blocking)   | Controlled (batched)  |
| Failure Recovery        | Immediate failure | Graceful degradation  |

---

## 📈 Scaling Path

TelemetryTaco is designed with a clear migration path from MVP to production scale, following proven patterns from [PostHog](https://posthog.com) and other high-scale telemetry platforms.

### Phase 1: PostgreSQL JSONB (Current)

**Use Case**: < 1M events/day, single region, real-time queries

**Architecture**:

- PostgreSQL with JSONB columns for event properties
- GIN indexes on JSONB fields for efficient querying
- Single PostgreSQL instance with read replicas for scaling reads

**Advantages**:

- ✅ Simple setup and operations
- ✅ ACID guarantees for data consistency
- ✅ Excellent for complex queries and aggregations
- ✅ No additional infrastructure required

**Limitations**:

- ⚠️ Write throughput limited to ~10K events/sec per instance
- ⚠️ JSONB query performance degrades with large datasets
- ⚠️ Storage costs grow linearly with event volume

### Phase 2: ClickHouse Migration (Future)

**Use Case**: > 10M events/day, multi-region, analytical workloads

**Architecture**:

- **Dual-Write Pattern**: Write to both PostgreSQL (for real-time) and ClickHouse (for analytics)
- **Event Router**: Celery task writes to both systems in parallel
- **Query Router**: Frontend queries PostgreSQL for recent data (< 24h), ClickHouse for historical
- **Eventual Consistency**: ClickHouse may lag by seconds, but provides 100x better query performance

**Migration Strategy**:

```python
# Example: Dual-write pattern in Celery task
@shared_task
def process_event_task(event_data: dict[str, Any]) -> None:
    # Write to PostgreSQL (real-time queries)
    Event.objects.create(**event_data)

    # Write to ClickHouse (analytical queries)
    clickhouse_client.insert('events', [event_data])
```

**ClickHouse Advantages**:

- ✅ **Columnar Storage**: 10-100x compression vs row-based storage
- ✅ **Query Performance**: Sub-second queries on billions of events
- ✅ **Horizontal Scaling**: Shard across multiple nodes
- ✅ **Time-Series Optimized**: Built-in functions for time-based aggregations
- ✅ **Cost Effective**: ~$0.01 per million events stored

**PostHog Architecture Reference**:

- PostHog uses ClickHouse for events table, PostgreSQL for metadata
- Events are immutable, append-only writes only
- Partitioning by date for efficient data retention policies
- Materialized views for common aggregations (daily/weekly/monthly)

### Phase 3: Advanced Optimizations

**Partitioning Strategy**:

- Partition ClickHouse tables by date (daily partitions)
- Automatic TTL policies for data retention
- Hot/warm storage tiers (SSD for recent, HDD for historical)

**Query Optimization**:

- Materialized views for pre-computed aggregations
- Sampling for exploratory queries on large datasets
- Approximate algorithms (HyperLogLog) for distinct counts

**Multi-Region**:

- Regional ClickHouse clusters with replication
- Event routing based on user geography
- Cross-region aggregation for global insights

### Migration Checklist

When to migrate to ClickHouse:

- [ ] Event volume exceeds 1M events/day consistently
- [ ] Query performance degrades (> 5s for aggregations)
- [ ] Storage costs become significant (> $500/month)
- [ ] Need for complex analytical queries (cohorts, funnels, retention)
- [ ] Multi-region deployment requirements

---

## 📚 Documentation

### API Endpoints

All API endpoints are rate-limited per IP address. Rate limits are configurable via environment variables and vary by environment (development has higher limits for testing).

#### `POST /api/capture`

Capture a new telemetry event. Events are queued asynchronously via Celery and return immediately.

**Request Body**:

```json
{
  "distinct_id": "user_123",
  "event_name": "feature_used",
  "properties": {
    "feature_name": "dark_mode",
    "page": "settings"
  }
}
```

**Response**: `200 OK`

```json
{
  "status": "ok"
}
```

**Rate Limiting**:

- **Production Default**: 1,000 requests per hour per IP address
- **Development Default**: 10,000 requests per hour per IP address
- **Configuration**: Set `RATE_LIMIT_CAPTURE_EVENT` environment variable (format: `"number/period"`, e.g., `"1000/h"`, `"100/m"`, `"5000/d"`)
- **Disable**: Set to `"0"` to disable rate limiting for this endpoint

#### `GET /api/events?limit=100`

List recent events (ordered by timestamp, descending).

**Query Parameters**:

- `limit` (optional): Maximum number of events to return (default: 100)

**Response**: `200 OK` - Array of event objects

**Rate Limiting**:

- **Production Default**: 10,000 requests per hour per IP address
- **Development Default**: 1,000,000 requests per hour per IP address
- **Configuration**: Set `RATE_LIMIT_LIST_EVENTS` environment variable

#### `GET /api/insights?lookback_minutes=60`

Get aggregated event counts grouped by minute for the specified lookback period.

**Query Parameters**:

- `lookback_minutes` (optional): Number of minutes to look back from now (default: 60)

**Response**: `200 OK` - Array of data points with `time` (HH:MM format) and `count`

**Rate Limiting**:

- **Production Default**: 300 requests per hour per IP address
- **Development Default**: 1,000 requests per hour per IP address
- **Configuration**: Set `RATE_LIMIT_GET_INSIGHTS` environment variable

### SDK Reference

The Python SDK is located in `sdk/telemetry_taco.py`. To use it:

```python
# Import from the SDK file
import sys
sys.path.insert(0, 'path/to/TelemetryTaco/sdk')
from telemetry_taco import TelemetryTaco

# Or install it as a package (recommended for production)
# pip install -e ./sdk
```

See [SDK Documentation](sdk/telemetry_taco.py) for full API reference.

### Development Guidelines

See [`.cursor/rules/generalguidelines.mdc`](.cursor/rules/generalguidelines.mdc) for:

- Frontend development standards (React + TypeScript)
- Backend development standards (Django + Django Ninja)
- Code quality and testing requirements

### Code Quality & Validation

Before submitting code, run validation commands to ensure quality:

```bash
# Validate backend (linting, formatting, Django checks)
pnpm validate:backend

# Validate frontend (linting, type checking)
pnpm validate:frontend

# Validate entire project
pnpm validate:all
```

The project uses:

- **Backend**: `ruff` for linting and formatting, Django's `check` command for configuration validation
- **Frontend**: `eslint` for linting, TypeScript compiler for type checking

### CI/CD

The project includes a GitHub Actions CI/CD pipeline (`.github/workflows/cicd.yml`) that automatically:

- Runs CodeQL security analysis for Python and JavaScript
- Validates code quality (linting, formatting, type checking)
- Runs tests for both backend and frontend
- Ensures all checks pass before merging

All pull requests must pass CI/CD validation before merging.

### Troubleshooting

#### Database Connection Issues

If you see "password authentication failed" errors:

1. **Check Docker PostgreSQL is running:**

   ```bash
   docker-compose ps db
   ```

2. **Verify database credentials:**

   ```bash
   docker-compose exec db env | grep POSTGRES
   ```

3. **Update `.env` file** in `backend/` with correct credentials:

   ```bash
   # The DATABASE_URL should match the credentials from step 2
   # Format: postgresql://USER:PASSWORD@localhost:5432/telemetry_taco
   ```

4. **Test connection using the diagnostic script:**
   ```bash
   cd backend
   poetry run python check_db.py
   ```

For more detailed troubleshooting, see [Backend Setup Guide](backend/SETUP.md).

#### Python Version Issues

If Poetry fails with Python version errors:

1. **Check your Python version:**

   ```bash
   python3 --version
   ```

2. **Configure Poetry to use Python 3.11:**

   ```bash
   cd backend
   poetry env use python3.11
   # Or: poetry env use /opt/homebrew/bin/python3.11
   ```

3. **Reinstall dependencies:**
   ```bash
   poetry install
   ```

#### Frontend Connection Issues

If you see "Failed to fetch" errors in the browser:

1. **Verify backend is running** on `http://localhost:8000`
2. **Check Vite proxy configuration** in `frontend/vite.config.ts`
3. **Verify CORS settings** in `backend/telemetry_taco/settings.py`
4. **Restart frontend dev server** after backend changes

---

## 🛠️ Tech Stack

### Backend

- **Python 3.11 or 3.12** - Runtime (Python 3.14+ not supported)
- **Django 5.0** - Web framework
- **Django Ninja** - Fast, type-safe API framework
- **Celery** - Distributed task queue
- **Redis** - Message broker and caching
- **PostgreSQL 16** - Primary database with JSONB support
- **Poetry** - Dependency management

### Frontend

- **React 18** - UI framework
- **TypeScript 5.3** - Type safety
- **Vite** - Build tool and dev server
- **Tailwind CSS** - Utility-first styling
- **Shadcn UI** - Component library
- **Recharts** - Data visualization

### Infrastructure

- **Docker Compose** - Local development environment
- **PostgreSQL 16** - Primary data store with JSONB support
- **Redis 7** - Task queue and caching

---

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

---

## 🙏 Acknowledgments

- Inspired by [PostHog](https://posthog.com)'s event ingestion architecture
- Built with modern Django patterns and best practices
- UI design follows developer-tool aesthetic principles

---

<div align="center">

**Made with 🌮 by developers, for developers**

[Report Bug](https://github.com/yourusername/TelemetryTaco/issues) • [Request Feature](https://github.com/yourusername/TelemetryTaco/issues) • [Documentation](https://github.com/yourusername/TelemetryTaco/wiki)

</div>
