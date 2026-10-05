from .base import *  # noqa: F403
from .base import env

DEBUG = env.bool("DEBUG", default=False)

DEFAULT_SECRET_KEY = "dev-only-secret-key-not-for-production-use-please-change-me-12345"

if SECRET_KEY == DEFAULT_SECRET_KEY:  # noqa: F405
    raise ValueError("SECRET_KEY must be set explicitly in production.")

if len(SECRET_KEY) < 50:  # noqa: F405
    raise ValueError("SECRET_KEY must be at least 50 characters long in production.")
