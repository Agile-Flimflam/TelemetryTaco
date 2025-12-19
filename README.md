# 🌮 TelemetryTaco

<div align="center">

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![Django](https://img.shields.io/badge/django-5.0+-green.svg)
![React](https://img.shields.io/badge/react-18.2.0-61dafb.svg)
![TypeScript](https://img.shields.io/badge/typescript-5.3.3-3178c6.svg)
![License](https://img.shields.io/badge/license-MIT-blue.svg)
![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)

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
    A[SDK] -->|HTTP POST| B[API Server]
    B -->|Queue Task| C[Redis]
    C -->|Consume| D[Celery Worker]
    D -->|Write| E[PostgreSQL]
    E -->|Query| F[Frontend Dashboard]

    style A fill:#f9a825
    style B fill:#f9a825
    style C fill:#dc2626
    style D fill:#f9a825
    style E fill:#336791
    style F fill:#61dafb
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

### Prerequisites

- Docker & Docker Compose
- Python 3.11+ (for local development)
- Node.js 18+ & pnpm (for frontend development)

### Docker Deployment (Recommended)

```bash
# Clone the repository
git clone https://github.com/yourusername/TelemetryTaco.git
cd TelemetryTaco

# Start all services
docker-compose up -d

# Run migrations
docker-compose exec backend python manage.py migrate

# Access the application
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# API Docs: http://localhost:8000/api/docs
```

### Local Development

#### Backend Setup

```bash
cd backend

# Install dependencies with Poetry
poetry install

# Set up environment variables
cp .env.example .env  # Edit as needed

# Run migrations
poetry run python manage.py migrate

# Start Django server
poetry run python manage.py runserver

# In another terminal, start Celery worker
poetry run celery -A core worker --loglevel=info
```

#### Frontend Setup

```bash
cd frontend

# Install dependencies
pnpm install

# Start development server
pnpm dev
```

### Using the SDK

```python
from telemetry_taco import TelemetryTaco

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

#### `POST /api/capture`

Capture a new telemetry event.

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

#### `GET /api/events?limit=100`

List recent events (ordered by timestamp, descending).

#### `GET /api/insights?lookback_minutes=60`

Get aggregated event counts grouped by minute.

### SDK Reference

See [SDK Documentation](sdk/telemetry_taco.py) for full API reference.

### Development Guidelines

See [`.cursor/rules/generalguidelines.mdc`](.cursor/rules/generalguidelines.mdc) for:

- Frontend development standards (React + TypeScript)
- Backend development standards (Django + Django Ninja)
- Code quality and testing requirements

---

## 🛠️ Tech Stack

### Backend

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
- **PostgreSQL** - Primary data store
- **Redis** - Task queue and caching

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
