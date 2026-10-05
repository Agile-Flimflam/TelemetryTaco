"""Gunicorn settings for the production image, read from the environment.

Gunicorn also reads GUNICORN_CMD_ARGS, which overrides anything here.
"""

import os

bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
# Gunicorn's own default is 1. Two per core suits this I/O-bound API.
workers = int(os.environ.get("WEB_CONCURRENCY", (os.cpu_count() or 1) * 2))
timeout = int(os.environ.get("GUNICORN_TIMEOUT", "30"))
# Log to stdout and stderr for `docker logs`.
accesslog = "-"
errorlog = "-"
