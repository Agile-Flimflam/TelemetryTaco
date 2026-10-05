from .base import *  # noqa: F403
from .base import LOGGING, env

DEBUG = env.bool("DEBUG", default=False)

DEFAULT_SECRET_KEY = "dev-only-secret-key-not-for-production-use-please-change-me-12345"

if SECRET_KEY == DEFAULT_SECRET_KEY:  # noqa: F405
    raise ValueError("SECRET_KEY must be set explicitly in production.")

if len(SECRET_KEY) < 50:  # noqa: F405
    raise ValueError("SECRET_KEY must be at least 50 characters long in production.")

# Gunicorn serves no static files, so WhiteNoise serves the admin's. It goes right after
# SecurityMiddleware, as its docs require.
MIDDLEWARE = [  # noqa: F405
    *MIDDLEWARE[:1],  # noqa: F405
    "whitenoise.middleware.WhiteNoiseMiddleware",
    *MIDDLEWARE[1:],  # noqa: F405
]

# Hashed, compressed copies made by collectstatic, so browsers can cache them forever.
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}

# JSON by default, for log collectors.
LOGGING["handlers"]["console"]["formatter"] = env("LOG_FORMAT", default="json")
