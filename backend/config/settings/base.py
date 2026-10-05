from pathlib import Path

import environ
from celery.schedules import crontab

BASE_DIR = Path(__file__).resolve().parent.parent.parent

env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, ["localhost", "127.0.0.1", "0.0.0.0"]),
)

environ.Env.read_env(BASE_DIR / ".env")

SECRET_KEY = env(
    "SECRET_KEY",
    default="dev-only-secret-key-not-for-production-use-please-change-me-12345",
)
DEBUG = env.bool("DEBUG", default=False)
ALLOWED_HOSTS = env.list("ALLOWED_HOSTS", default=["localhost", "127.0.0.1", "0.0.0.0"])
TIME_ZONE = env("TIME_ZONE", default="UTC")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "corsheaders",
    "events",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    }
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default="postgresql://postgres:postgres@localhost:5432/telemetry_taco",
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {
        "NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.MinimumLengthValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.CommonPasswordValidator",
    },
    {
        "NAME": "django.contrib.auth.password_validation.NumericPasswordValidator",
    },
]

LANGUAGE_CODE = "en-us"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])
CORS_ALLOW_CREDENTIALS = True
CORS_ALLOW_HEADERS = [
    "accept",
    "accept-encoding",
    "authorization",
    "content-type",
    "dnt",
    "origin",
    "user-agent",
    "x-csrftoken",
    "x-requested-with",
]

REDIS_URL = env("REDIS_URL", default="redis://localhost:6379/0")

CELERY_BROKER_URL = REDIS_URL
CELERY_RESULT_BACKEND = REDIS_URL
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_TASK_ALWAYS_EAGER = env.bool("CELERY_TASK_ALWAYS_EAGER", default=False)
CELERY_TASK_EAGER_PROPAGATES = env.bool("CELERY_TASK_EAGER_PROPAGATES", default=False)

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": env("CACHE_URL", default="redis://localhost:6379/1"),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

RATELIMIT_USE_CACHE = "default"
RATELIMIT_IP_META_KEY = "events.api.ratelimit.client_ip"
# Number of reverse proxies in front of the app. 0 keys rate limits on REMOTE_ADDR and ignores
# X-Forwarded-For, which a client can forge. Only raise it when every request passes through
# that many proxies, each appending to X-Forwarded-For.
TRUSTED_PROXY_COUNT = env.int("TRUSTED_PROXY_COUNT", default=0)

# Rates are per client IP. The dashboard polls /api/events, /api/insights and /api/stats, and
# frontend/src/shared/api/polling.test.ts fails if its intervals use more than half of these.
RATE_LIMIT_CAPTURE_EVENT = env("RATE_LIMIT_CAPTURE_EVENT", default="1000/h")
RATE_LIMIT_LIST_EVENTS = env("RATE_LIMIT_LIST_EVENTS", default="10000/h")
RATE_LIMIT_GET_INSIGHTS = env("RATE_LIMIT_GET_INSIGHTS", default="1000/h")

MAX_CAPTURE_BATCH_SIZE = env.int("MAX_CAPTURE_BATCH_SIZE", default=500)
MAX_EVENT_PROPERTIES_BYTES = env.int("MAX_EVENT_PROPERTIES_BYTES", default=32 * 1024)
MAX_EVENTS_LIMIT = env.int("MAX_EVENTS_LIMIT", default=200)
MAX_INSIGHTS_LOOKBACK_MINUTES = env.int("MAX_INSIGHTS_LOOKBACK_MINUTES", default=24 * 60)
EVENT_RETENTION_DAYS = env.int("EVENT_RETENTION_DAYS", default=30)
EVENT_RETENTION_DELETE_BATCH_SIZE = env.int("EVENT_RETENTION_DELETE_BATCH_SIZE", default=10_000)

# Needs exactly one beat process, `celery -A config beat`, as in docker-compose.yml and
# Procfile.dev. Hourly keeps each purge small.
CELERY_BEAT_SCHEDULE = {
    "purge-expired-events": {
        "task": "events.tasks.events.purge_expired_events_task",
        "schedule": crontab(minute=17),
    },
}

# LOG_FORMAT is "text" (readable) or "json" (one object per line, for log collectors).
# Both keep the fields passed with logger.info(..., extra={...}).
LOG_FORMAT = env("LOG_FORMAT", default="text")
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "text": {"()": "config.logging.TextFormatter"},
        "json": {"()": "config.logging.JsonFormatter"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": LOG_FORMAT,
        }
    },
    # On the root logger so Celery's own loggers use it too (config/celery.py stops Celery
    # from installing its handlers).
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}
