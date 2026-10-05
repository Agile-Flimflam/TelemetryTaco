"""Docker HEALTHCHECK for the production image.

The same image runs the API, the Celery worker and beat, and the healthcheck runs in all of
them. Only the API serves HTTP, so the others report healthy instead of failing the probe.
"""

import os
import sys
import urllib.request


def main() -> int:
    with open("/proc/1/cmdline", "rb") as cmdline:
        if b"gunicorn" not in cmdline.read():
            return 0

    url = f"http://localhost:{os.environ.get('PORT', '8000')}/api/health/live"
    try:
        # A fixed http:// URL on localhost, so B310's file:// concern doesn't apply.
        with urllib.request.urlopen(url, timeout=4):  # nosec B310
            return 0
    except OSError:
        return 1


if __name__ == "__main__":
    sys.exit(main())
