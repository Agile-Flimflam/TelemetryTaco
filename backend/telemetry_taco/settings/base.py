from pathlib import Path

import environ

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
    "core",
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

ROOT_URLCONF = "telemetry_taco.urls"

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

WSGI_APPLICATION = "telemetry_taco.wsgi.application"
ASGI_APPLICATION = "telemetry_taco.asgi.application"

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

RATE_LIMIT_CAPTURE_EVENT = env("RATE_LIMIT_CAPTURE_EVENT", default="1000/h")
RATE_LIMIT_LIST_EVENTS = env("RATE_LIMIT_LIST_EVENTS", default="10000/h")
RATE_LIMIT_GET_INSIGHTS = env("RATE_LIMIT_GET_INSIGHTS", default="300/h")

MAX_CAPTURE_BATCH_SIZE = env.int("MAX_CAPTURE_BATCH_SIZE", default=500)
MAX_EVENT_PROPERTIES_BYTES = env.int("MAX_EVENT_PROPERTIES_BYTES", default=32 * 1024)
MAX_EVENTS_LIMIT = env.int("MAX_EVENTS_LIMIT", default=200)
MAX_INSIGHTS_LOOKBACK_MINUTES = env.int("MAX_INSIGHTS_LOOKBACK_MINUTES", default=24 * 60)
EVENT_RETENTION_DAYS = env.int("EVENT_RETENTION_DAYS", default=30)

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {
            "format": (
                "%(asctime)s %(levelname)s %(name)s "
                "event=%(message)s task=%(task_name)s task_id=%(task_id)s"
            ),
        },
        "default": {
            "format": "%(asctime)s %(levelname)s %(name)s %(message)s",
        },
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "formatter": "default",
        }
    },
    "loggers": {
        "core": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
        "celery": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
    },
}
