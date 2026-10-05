# The default (last) stage is the production image: gunicorn, as a non-root user, with only
# the main dependencies. docker-compose.yml builds the `dev` stage instead.

FROM python:3.13-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app


FROM base AS builder

# Exact pin for reproducible builds. Keep in sync with POETRY_VERSION in ci.yml and the
# version that wrote poetry.lock.
ENV POETRY_NO_INTERACTION=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_CACHE_DIR=/tmp/poetry-cache
RUN pip install --no-cache-dir "poetry==2.2.1" \
    && python -m venv /opt/venv

COPY pyproject.toml poetry.lock ./
# Poetry installs into the active venv (VIRTUAL_ENV), which the later stages copy whole.
# psycopg ships binary wheels, so no compiler is needed.
RUN poetry install --only main --no-root && rm -rf "$POETRY_CACHE_DIR"


# Local development: dev dependencies too, for runserver, the test suite and seed_events.
FROM builder AS dev

RUN poetry install --no-root && rm -rf "$POETRY_CACHE_DIR"
COPY . .
EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]


FROM base AS runtime

RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin app

COPY --from=builder /opt/venv /opt/venv
COPY . .

ENV DJANGO_SETTINGS_MODULE=config.settings.production
# collectstatic only copies files, but production settings refuse to load without a real
# SECRET_KEY, so give this one command a throwaway key.
RUN SECRET_KEY="collectstatic-only-$(python -c 'import secrets; print(secrets.token_hex(32))')" \
    python manage.py collectstatic --noinput

USER app
EXPOSE 8000
# Probes /api/health/live in the API process; worker and beat containers report healthy.
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s --retries=3 \
    CMD ["python", "healthcheck.py"]
# Run the worker and beat from this image with `celery -A config worker` and
# `celery -A config beat --schedule /tmp/celerybeat-schedule` (/app isn't writable).
CMD ["gunicorn", "config.wsgi"]
