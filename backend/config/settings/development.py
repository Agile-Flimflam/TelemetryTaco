from .base import *  # noqa: F403
from .base import env

DEBUG = env.bool("DEBUG", default=True)

if not CORS_ALLOWED_ORIGINS:  # noqa: F405
    CORS_ALLOWED_ORIGINS = [  # noqa: F405
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

RATE_LIMIT_CAPTURE_EVENT = env("RATE_LIMIT_CAPTURE_EVENT", default="10000/h")
RATE_LIMIT_LIST_EVENTS = env("RATE_LIMIT_LIST_EVENTS", default="1000000/h")
RATE_LIMIT_GET_INSIGHTS = env("RATE_LIMIT_GET_INSIGHTS", default="1000/h")
