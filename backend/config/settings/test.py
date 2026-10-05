from .base import *  # noqa: F403

DEBUG = False
SECRET_KEY = "test-secret-key-not-for-production-use-only-12345678901234567890"

# In-memory SQLite by default; CI sets TEST_DATABASE_URL to run the suite against Postgres.
DATABASES = {  # noqa: F405
    "default": env.db("TEST_DATABASE_URL", default="sqlite://:memory:"),  # noqa: F405
}

CACHES = {  # noqa: F405
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "telemetry-taco-test",
    }
}

PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]

CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_EAGER_PROPAGATES = True

RATE_LIMIT_CAPTURE_EVENT = "999999/h"
RATE_LIMIT_LIST_EVENTS = "999999/h"
RATE_LIMIT_GET_INSIGHTS = "999999/h"
