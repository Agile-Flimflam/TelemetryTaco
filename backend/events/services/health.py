from django.core.cache import caches
from django.db import connections

from events.api.schemas import HealthStatusResponse


def get_liveness_status() -> HealthStatusResponse:
    return HealthStatusResponse(status="ok", database="unchecked", cache="unchecked")


def get_readiness_status() -> HealthStatusResponse:
    database_status = "ok"
    cache_status = "ok"

    try:
        with connections["default"].cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
    except Exception:
        database_status = "error"

    try:
        cache = caches["default"]
        cache.set("healthcheck", "ok", timeout=5)
        if cache.get("healthcheck") != "ok":
            cache_status = "error"
    except Exception:
        cache_status = "error"

    status = "ok" if database_status == "ok" and cache_status == "ok" else "degraded"
    return HealthStatusResponse(status=status, database=database_status, cache=cache_status)
